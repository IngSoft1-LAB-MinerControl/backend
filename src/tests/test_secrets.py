"""
Exhaustive tests for the Secret endpoints and services, using pytest fixtures for isolation.
"""
import datetime
import pytest
from unittest.mock import patch, AsyncMock

from src.database.models import Game, Player, Secrets
from src.database.services.services_secrets import init_secrets, deal_secrets_to_players

@pytest.fixture
def setup_data(db_session):
    """
    Fixture to create a consistent set of data for secret-related tests.
    This runs for each test, ensuring a clean state.
    """
    game = Game(game_id=1, name="Secret Game", status="in course", max_players=4, min_players=2, players_amount=4)
    
    player1 = Player(player_id=1, name="Secret Player", host=True, birth_date=datetime.date(2000, 1, 1), game_id=1, turn_order=1, social_disgrace=False)
    murderer_secret = Secrets(secret_id=1, murderer=True, acomplice=False, revelated=False, player_id=1, game_id=1)
    revealed_secret = Secrets(secret_id=2, murderer=False, acomplice=False, revelated=True, player_id=1, game_id=1)
    not_revealed_secret = Secrets(secret_id=3, murderer=False, acomplice=False, revelated=False, player_id=1, game_id=1)

    player2 = Player(player_id=2, name="Innocent Player", host=False, birth_date=datetime.date(2001, 1, 1), game_id=1, turn_order=2, social_disgrace=False)
    
    player3 = Player(player_id=3, name="Target Player", host=False, birth_date=datetime.date(2002, 2, 2), game_id=1, turn_order=3, social_disgrace=False)
    
    player4_all_revealed = Player(player_id=4, name="Disgraced Player", host=False, birth_date=datetime.date(2003, 3, 3), game_id=1, turn_order=4, social_disgrace=True)
    p4_secret1 = Secrets(secret_id=4, murderer=False, acomplice=False, revelated=True, player_id=4, game_id=1)
    p4_secret2 = Secrets(secret_id=5, murderer=False, acomplice=False, revelated=True, player_id=4, game_id=1)

    db_session.add_all([game, player1, player2, player3, player4_all_revealed, murderer_secret, revealed_secret, not_revealed_secret, p4_secret1, p4_secret2])
    db_session.commit()


# --- Tests for Listing Secrets ---

def test_list_secrets_of_player_success(client, setup_data):
    """Verifies that secrets for a specific player can be listed."""
    response = client.get("/lobby/secrets/1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    assert {s['secret_id'] for s in data} == {1, 2, 3}

def test_list_secrets_of_player_with_no_secrets(client, setup_data):
    """Verifies the 404 response when a player has no secrets."""
    response = client.get("/lobby/secrets/2")
    assert response.status_code == 404
    assert "No secrets found" in response.json()["detail"]

def test_list_secrets_of_nonexistent_player(client):
    """Verifies the 404 response for a player that does not exist."""
    response = client.get("/lobby/secrets/999")
    assert response.status_code == 404
    assert "Player not found" in response.json()["detail"]

def test_list_secrets_of_game_success(client, setup_data):
    """Verifies that all secrets for a specific game can be listed."""
    response = client.get("/lobby/secrets_game/1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5

def test_list_secrets_of_game_with_no_secrets(client, db_session):
    """Verifies the 404 response for a game that has no secrets or does not exist."""
    game = Game(game_id=99, name="Empty Game", max_players=4, min_players=2, players_amount=0)
    db_session.add(game)
    db_session.commit()
    response = client.get("/lobby/secrets_game/99")
    assert response.status_code == 404
    assert "No secrets found" in response.json()["detail"]


# --- Tests for Revealing a Secret ---

@pytest.mark.asyncio
async def test_reveal_secret_success(client, setup_data, mocker):
    """Verifies that a secret can be revealed successfully."""
    mocker.patch('src.routes.secrets_routes.broadcast_game_information', new_callable=AsyncMock)
    response = client.put("/secrets/reveal/3")
    assert response.status_code == 200
    assert response.json()["revelated"] is True

@pytest.mark.asyncio
async def test_reveal_murderer_secret_finishes_game(client, setup_data, mocker):
    """Verifies that revealing the murderer's secret triggers the end of the game."""
    mock_finish_game = mocker.patch('src.database.services.services_secrets.finish_game', new_callable=AsyncMock)
    mocker.patch('src.routes.secrets_routes.broadcast_game_information', new_callable=AsyncMock)
    
    response = client.put("/secrets/reveal/1")
    assert response.status_code == 200
    mock_finish_game.assert_awaited_once_with(1, mocker.ANY)

@pytest.mark.asyncio
async def test_reveal_secret_not_found(client):
    """Verifies the 404 error when trying to reveal a non-existent secret."""
    response = client.put("/secrets/reveal/999")
    assert response.status_code == 404
    assert "Secret not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_reveal_secret_already_revealed(client, setup_data):
    """Verifies that a secret that is already revealed cannot be revealed again."""
    response = client.put("/secrets/reveal/2")
    assert response.status_code == 400
    assert "Secret is already revealed" in response.json()["detail"]


# --- Tests for Hiding a Secret ---

@pytest.mark.asyncio
async def test_hide_secret_success(client, setup_data, mocker):
    """Verifies that a revealed secret can be hidden."""
    mocker.patch('src.routes.secrets_routes.broadcast_game_information', new_callable=AsyncMock)
    response = client.put("/secrets/hide/2")
    assert response.status_code == 200
    assert response.json()["revelated"] is False

@pytest.mark.asyncio
async def test_hide_secret_not_found(client):
    """Verifies the 404 error when trying to hide a non-existent secret."""
    response = client.put("/secrets/hide/999")
    assert response.status_code == 404
    assert "Secret not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_hide_secret_not_revealed(client, setup_data):
    """Verifies that a secret that is not revealed cannot be hidden."""
    response = client.put("/secrets/hide/1")
    assert response.status_code == 400
    assert "Secret is not revealed" in response.json()["detail"]


# --- Tests for Stealing a Secret ---

@pytest.mark.asyncio
async def test_steal_secret_success(client, setup_data, mocker):
    """Verifies that a player can steal a revealed secret from another."""
    mocker.patch('src.routes.secrets_routes.broadcast_game_information', new_callable=AsyncMock)
    response = client.put("/secrets/steal/2,3")
    assert response.status_code == 200
    data = response.json()
    assert data["player_id"] == 3
    assert data["revelated"] is False

@pytest.mark.asyncio
async def test_steal_secret_must_be_revealed(client, setup_data):
    """Verifies that a secret must be revealed to be stolen."""
    response = client.put("/secrets/steal/1,3")
    assert response.status_code == 400
    assert "Secret must be revealed to be stolen" in response.json()["detail"]

@pytest.mark.asyncio
async def test_steal_secret_target_player_not_found(client, setup_data):
    """Verifies the 404 error when the target player does not exist."""
    response = client.put("/secrets/steal/2,999")
    assert response.status_code == 404
    assert "Player not found" in response.json()["detail"]


# --- Tests for Social Disgrace ---

@pytest.mark.asyncio
async def test_social_disgrace_becomes_true_on_last_secret_reveal(client, setup_data, db_session, mocker):
    """Verifies social_disgrace becomes True when a player's last secret is revealed."""
    mocker.patch('src.routes.secrets_routes.broadcast_game_information', new_callable=AsyncMock)
    
    # Player 1 has secrets 1 (hidden), 2 (revealed), 3 (hidden)
    # Reveal secret 1
    client.put("/secrets/reveal/1")
    # Reveal secret 3
    client.put("/secrets/reveal/3")

    db_session.refresh(db_session.get(Player, 1))
    player1 = db_session.get(Player, 1)
    assert player1.social_disgrace is True

@pytest.mark.asyncio
async def test_social_disgrace_becomes_false_when_secret_is_hidden(client, setup_data, db_session, mocker):
    """Verifies social_disgrace becomes False when a secret is hidden for a disgraced player."""
    mocker.patch('src.routes.secrets_routes.broadcast_game_information', new_callable=AsyncMock)
    
    # Player 4 has all secrets revealed (4, 5)
    player4 = db_session.get(Player, 4)
    assert player4.social_disgrace is True

    # Hide one of their secrets
    client.put("/secrets/hide/4")

    player4 = db_session.get(Player, 4)
    assert player4.social_disgrace is False

@pytest.mark.asyncio
async def test_social_disgrace_updates_on_steal(client, setup_data, db_session, mocker):
    """Verifies social_disgrace is updated for both players when a secret is stolen."""
    mocker.patch('src.routes.secrets_routes.broadcast_game_information', new_callable=AsyncMock)
    
    # Player 4 starts in disgrace. Player 3 does not.
    player4 = db_session.get(Player, 4)
    player3 = db_session.get(Player, 3)
    assert player4.social_disgrace is True
    assert player3.social_disgrace is False
    
    # Player 3 steals a secret from Player 4
    client.put("/secrets/steal/4,3") # Steal secret 4, give to player 3

    player4 = db_session.get(Player, 4)
    player3 = db_session.get(Player, 3)

    print (f"Player 4 disgrace: {player4.social_disgrace}, Player 3 disgrace: {player3.social_disgrace}")
    # Player 4 should continue in social disgrace
    assert player4.social_disgrace is True
    # Player 3 now has a new hidden secret, so they remain not in disgrace
    assert player3.social_disgrace is False

@pytest.mark.asyncio
async def test_player_with_no_secrets_not_in_disgrace(client, setup_data, db_session):
    """Verifies a player with no secrets does not trigger social disgrace."""
    player2 = db_session.get(Player, 2)
    assert not player2.secrets
    assert player2.social_disgrace is False


# --- Tests for Service Layer Logic ---

def test_init_secrets_less_than_5_players(db_session):
    """Verifies that N*3 secrets are created without an accomplice for 2-4 players."""
    game = Game(game_id=2, name="4 Players Game", status="waiting", max_players=4, min_players=2, players_amount=4)
    for i in range(4):
        db_session.add(Player(name=f"P{i}", game=game, birth_date=datetime.date(2000, 1, 1)))
    db_session.commit()

    init_secrets(game.game_id, db_session)
    
    secrets = db_session.query(Secrets).filter(Secrets.game_id == game.game_id).all()
    assert len(secrets) == 12
    assert any(s.murderer for s in secrets)
    assert not any(s.acomplice for s in secrets)

def test_init_secrets_more_than_4_players(db_session):
    """Verifies that N*3 secrets are created WITH an accomplice for 5+ players."""
    game = Game(game_id=3, name="5 Players Game", status="waiting", max_players=5, min_players=5, players_amount=5)
    for i in range(5):
        db_session.add(Player(name=f"P{i}", game=game, birth_date=datetime.date(2000, 1, 1)))
    db_session.commit()

    init_secrets(game.game_id, db_session)
    
    secrets = db_session.query(Secrets).filter(Secrets.game_id == game.game_id).all()
    assert len(secrets) == 15
    assert any(s.murderer for s in secrets)
    assert any(s.acomplice for s in secrets)

def test_deal_secrets_avoids_murderer_and_acomplice_on_same_player(db_session):
    """Verifies that the dealing logic prevents the murderer and accomplice from being the same player."""
    game = Game(game_id=4, name="Deal Test Game", status="waiting", max_players=5, min_players=5, players_amount=5)
    players = [Player(name=f"P{i}", game=game, birth_date=datetime.date(2000, 1, 1)) for i in range(5)]
    db_session.add_all(players)
    db_session.commit()
    init_secrets(game.game_id, db_session)

    deal_secrets_to_players(game.game_id, db_session)

    murderer_secret = db_session.query(Secrets).filter(Secrets.game_id == game.game_id, Secrets.murderer == True).one_or_none()
    acomplice_secret = db_session.query(Secrets).filter(Secrets.game_id == game.game_id, Secrets.acomplice == True).one_or_none()

    assert murderer_secret is not None
    assert acomplice_secret is not None
    assert murderer_secret.player_id is not None
    assert acomplice_secret.player_id is not None
    assert murderer_secret.player_id != acomplice_secret.player_id