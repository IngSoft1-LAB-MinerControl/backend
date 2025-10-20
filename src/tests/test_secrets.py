"""
Exhaustive tests for the Secret endpoints and services, using pytest fixtures for isolation.
"""
import datetime
import pytest
from unittest.mock import patch, AsyncMock

# Import only the necessary models and services for testing.
# The TestClient (client) and db_session are provided by fixtures from conftest.py.
from src.database.models import Game, Player, Secrets
from src.database.services.services_secrets import init_secrets, deal_secrets_to_players

@pytest.fixture
def setup_data(db_session):
    """
    Fixture to create a consistent set of data for secret-related tests.
    This runs for each test, ensuring a clean state.
    """
    # Arrange: Create a game, players, and secrets for various scenarios
    game = Game(game_id=1, name="Secret Game", status="in course", max_players=4, min_players=2, players_amount=3)
    
    # Player 1 has a hidden murderer secret and a revealed normal secret
    player1 = Player(player_id=1, name="Secret Player", host=True, birth_date=datetime.date(2000, 1, 1), game_id=1, turn_order=1)
    murderer_secret = Secrets(secret_id=1, murderer=True, acomplice=False, revelated=False, player_id=1, game_id=1)
    revealed_secret = Secrets(secret_id=2, murderer=False, acomplice=False, revelated=True, player_id=1, game_id=1)
    not_revealed_secret = Secrets(secret_id=3, murderer=False, acomplice=False, revelated=False, player_id=1, game_id=1)

    # Player 2 has no secrets initially
    player2 = Player(player_id=2, name="Innocent Player", host=False, birth_date=datetime.date(2001, 1, 1), game_id=1, turn_order=2)
    
    # Player 3 is a target for stealing secrets
    player3 = Player(player_id=3, name="Target Player", host=False, birth_date=datetime.date(2002, 2, 2), game_id=1, turn_order=3)
    
    db_session.add_all([game, player1, player2, player3, murderer_secret, revealed_secret, not_revealed_secret])
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
    assert len(data) == 3

def test_list_secrets_of_game_with_no_secrets(client):
    """Verifies the 404 response for a game that has no secrets or does not exist."""
    response = client.get("/lobby/secrets_game/999")
    assert response.status_code == 404
    assert "No secrets found" in response.json()["detail"]


# --- Tests for Revealing a Secret ---

@pytest.mark.asyncio
async def test_reveal_secret_success(client, setup_data, mocker):
    """Verifies that a secret can be revealed successfully."""
    mocker.patch('src.routes.secrets_routes.broadcast_game_information', new_callable=AsyncMock)
    # Secret 2 is the murderer secret, but not revealed yet
    response = client.put("/secrets/reveal/3")
    if response.status_code!=200:
        print(response.json())
    assert response.status_code == 200
    assert response.json()["revelated"] is True

@pytest.mark.asyncio
async def test_reveal_murderer_secret_finishes_game(client, setup_data, mocker):
    """Verifies that revealing the murderer's secret triggers the end of the game."""
    mock_finish_game = mocker.patch('src.database.services.services_secrets.finish_game', new_callable=AsyncMock)
    mocker.patch('src.routes.secrets_routes.broadcast_game_information', new_callable=AsyncMock)
    
    response = client.put("/secrets/reveal/1") # Secret 1 is the murderer
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
    # Secret 2 is already revealed in the fixture
    response = client.put("/secrets/reveal/2")
    assert response.status_code == 400
    assert "Secret is already revealed" in response.json()["detail"]


# --- Tests for Hiding a Secret ---

@pytest.mark.asyncio
async def test_hide_secret_success(client, setup_data, mocker):
    """Verifies that a revealed secret can be hidden."""
    mocker.patch('src.routes.secrets_routes.broadcast_game_information', new_callable=AsyncMock)
    # Secret 2 is revealed in the fixture
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
    # Secret 1 is not revealed in the fixture
    response = client.put("/secrets/hide/1")
    assert response.status_code == 400
    assert "Secret is not revealed" in response.json()["detail"]


# --- Tests for Stealing a Secret ---

@pytest.mark.asyncio
async def test_steal_secret_success(client, setup_data, mocker):
    """Verifies that a player can steal a revealed secret from another."""
    mocker.patch('src.routes.secrets_routes.broadcast_game_information', new_callable=AsyncMock)
    # Steal secret 2 (which is revealed) and give it to player 3
    response = client.put("/secrets/steal/2,3")
    assert response.status_code == 200
    data = response.json()
    assert data["player_id"] == 3
    assert data["revelated"] is False # Secret should be hidden after being stolen

@pytest.mark.asyncio
async def test_steal_secret_must_be_revealed(client, setup_data):
    """Verifies that a secret must be revealed to be stolen."""
    # Secret 1 is not revealed
    response = client.put("/secrets/steal/1,3")
    assert response.status_code == 400
    assert "Secret must be revealed to be stolen" in response.json()["detail"]

@pytest.mark.asyncio
async def test_steal_secret_target_player_not_found(client, setup_data):
    """Verifies the 404 error when the target player does not exist."""
    response = client.put("/secrets/steal/2,999")
    assert response.status_code == 404
    assert "Player not found" in response.json()["detail"]


# --- Tests for Service Layer Logic ---

def test_init_secrets_less_than_5_players(db_session):
    """Verifies that N*3 secrets are created without an accomplice for 2-4 players."""
    game = Game(game_id=2, name="4 Players Game", status="waiting", max_players=4, min_players=2, players_amount=4)
    for i in range(4):
        db_session.add(Player(name=f"P{i}", game=game, birth_date=datetime.date(2000, 1, 1)))
    db_session.commit()

    init_secrets(game.game_id, db_session)
    
    secrets = db_session.query(Secrets).filter(Secrets.game_id == game.game_id).all()
    assert len(secrets) == 12  # 4 players * 3 secrets
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
    assert len(secrets) == 15  # 5 players * 3 secrets
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

    murderer_secret = db_session.query(Secrets).filter(Secrets.game_id == game.game_id, Secrets.murderer == True).one()
    acomplice_secret = db_session.query(Secrets).filter(Secrets.game_id == game.game_id, Secrets.acomplice == True).one()

    assert murderer_secret.player_id is not None
    assert acomplice_secret.player_id is not None
    assert murderer_secret.player_id != acomplice_secret.player_id