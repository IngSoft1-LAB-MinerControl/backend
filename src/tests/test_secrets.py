"""
Tests for the Secret endpoints and services, using pytest fixtures for isolation.
"""
import datetime
import pytest
from unittest.mock import patch, AsyncMock
import asyncio

# Import only the necessary models for setting up test data.
# The TestClient and db_session are provided by fixtures from conftest.py.
from src.database.models import Game, Player, Secrets
from src.database.services.services_secrets import deal_secrets_to_players, init_secrets

@pytest.fixture
def setup_data(db_session):
    """
    Fixture to create a consistent set of data for secret-related tests.
    This runs for each test, ensuring a clean state.
    """
    # Arrange: Create a game, players, and secrets
    game = Game(game_id=1, name="Secret Game", status="in course", max_players=4, min_players=2, players_amount=3)
    
    # Player 1 has two secrets, one not revealed, one already revealed
    player1 = Player(player_id=1, name="Secret Player", host=True, birth_date=datetime.date(2000, 1, 1), game_id=1, turn_order=1)
    secret1 = Secrets(secret_id=1, murderer=True, acomplice=False, revelated=False, player_id=1, game_id=1)
    secret2 = Secrets(secret_id=2, murderer=False, acomplice=False, revelated=True, player_id=1, game_id=1)
    
    # Player 2 has no secrets
    player2 = Player(player_id=2, name="Innocent Player", host=False, birth_date=datetime.date(2001, 1, 1), game_id=1, turn_order=2)
    
    # Player 3 is a target for stealing
    player3 = Player(player_id=3, name="Target Player", host=False, birth_date=datetime.date(2002, 2, 2), game_id=1, turn_order=3)
    
    db_session.add_all([game, player1, player2, player3, secret1, secret2])
    db_session.commit()


# --- Tests for Listing Secrets ---

def test_list_secrets_of_player_success(client, setup_data):
    """Verifica que se pueden listar los secretos de un jugador."""
    response = client.get("/lobby/secrets/1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["secret_id"] == 1

def test_list_secrets_of_player_with_no_secrets(client, setup_data):
    """Verifica la respuesta cuando un jugador no tiene secretos."""
    response = client.get("/lobby/secrets/2")
    assert response.status_code == 404
    assert "No secrets found" in response.json()["detail"]

def test_list_secrets_of_nonexistent_player(client):
    """Verifica la respuesta para un jugador que no existe."""
    response = client.get("/lobby/secrets/999")
    assert response.status_code == 404
    assert "Player not found" in response.json()["detail"]

def test_list_secrets_of_game_success(client, setup_data):
    """Verifica que se pueden listar todos los secretos de una partida."""
    response = client.get("/lobby/secrets_game/1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["game_id"] == 1

def test_list_secrets_of_game_with_no_secrets(client):
    """Verifica la respuesta para una partida sin secretos o inexistente."""
    response = client.get("/lobby/secrets_game/999")
    assert response.status_code == 404
    assert "No secrets found" in response.json()["detail"]


# --- Tests for Revelating a Secret ---

def test_revelate_secret_success(client, setup_data):
    """Verifica que un secreto puede ser revelado exitosamente."""
    response = client.put("/secrets/reveal/1")
    assert response.status_code == 200
    assert response.json()["revelated"] is True

def test_reveal_secret_not_found(client):
    """Verifica el error al intentar revelar un secreto inexistente."""
    response = client.put("/secrets/reveal/999")
    assert response.status_code == 404
    assert "Secret not found" in response.json()["detail"]

def test_reveal_secret_already_revealed(client, setup_data):
    """Verifica que no se puede revelar un secreto que ya está revelado."""
    # The secret with ID 2 is already revealed in the setup_data fixture
    response = client.put("/secrets/reveal/2")
    assert response.status_code == 400
    assert "Secret is already revealed" in response.json()["detail"]


# --- Tests for Hiding a Secret ---

def test_hide_secret_success(client, setup_data):
    """Verifica que un secreto revelado puede ser ocultado."""
    response = client.put("/secrets/hide/2")
    assert response.status_code == 200
    assert response.json()["revelated"] is False

def test_hide_secret_not_found(client):
    """Verifica el error al intentar ocultar un secreto inexistente."""
    response = client.put("/secrets/hide/999")
    assert response.status_code == 404
    assert "Secret not found" in response.json()["detail"]

def test_hide_secret_not_revelated(client, setup_data):
    """Verifica que no se puede ocultar un secreto que no está revelado."""
    # The secret with ID 1 is not revelated in the fixture
    response = client.put("/secrets/hide/1")
    assert response.status_code == 400
    assert "Secret is not revealed" in response.json()["detail"]


# --- Tests for Stealing a Secret ---

def test_steal_secret_success(client, setup_data):
    """Verifica que un jugador puede robar un secreto a otro."""
    # Steal secret 2 (which is revealed) and give it to player 3
    response = client.put("/secrets/steal/2,3")
    assert response.status_code == 200
    assert response.json()["player_id"] == 3

def test_steal_secret_not_found(client):
    """Verifica el error al intentar robar un secreto inexistente."""
    response = client.put("/secrets/steal/999,3")
    assert response.status_code == 404
    assert "Secret not found" in response.json()["detail"]

def test_steal_secret_target_player_not_found(client, setup_data):
    """Verifica el error al intentar dar un secreto a un jugador inexistente."""
    response = client.put("/secrets/steal/1,999")
    assert response.status_code == 400
    assert "Secret must be revealed to be stolen" in response.json()["detail"]


# --- Tests for Game Initialization Logic ---s

def test_init_secrets_less_than_5_players(db_session):
    """Verifica que se crean N*3 secretos sin cómplice para 2-4 jugadores."""
    game = Game(name="4 Players Game", status="waiting", max_players=4, min_players=2, players_amount=4)
    for i in range(4):
        db_session.add(Player(name=f"P{i}", game=game, birth_date=datetime.date(2000, 1, 1)))
    db_session.commit()

    init_secrets(game.game_id, db_session)
    
    secrets = db_session.query(Secrets).filter(Secrets.game_id == game.game_id).all()
    assert len(secrets) == 12  # 4 players * 3 secrets
    assert any(s.murderer for s in secrets)
    assert not any(s.acomplice for s in secrets)

def test_init_secrets_more_than_4_players(db_session):
    """Verifica que se crean N*3 secretos CON cómplice para 5+ jugadores."""
    game = Game(name="5 Players Game", status="waiting", max_players=5, min_players=5, players_amount=5)
    for i in range(5):
        db_session.add(Player(name=f"P{i}", game=game, birth_date=datetime.date(2000, 1, 1)))
    db_session.commit()

    init_secrets(game.game_id, db_session)
    
    secrets = db_session.query(Secrets).filter(Secrets.game_id == game.game_id).all()
    assert len(secrets) == 15  # 5 players * 3 secrets
    assert any(s.murderer for s in secrets)
    assert any(s.acomplice for s in secrets)

def test_deal_secrets_avoids_murderer_and_acomplice_on_same_player(db_session):
    """Verifica que la repartición evita asignar asesino y cómplice al mismo jugador."""
    game = Game(name="Deal Test Game", status="waiting", max_players=5, min_players=5, players_amount=5)
    for i in range(5):
        db_session.add(Player(name=f"P{i}", game=game, birth_date=datetime.date(2000, 1, 1)))
    db_session.commit()
    init_secrets(game.game_id, db_session)

    deal_secrets_to_players(game.game_id, db_session)

    murderer_secret = db_session.query(Secrets).filter(Secrets.game_id == game.game_id, Secrets.murderer == True).one()
    acomplice_secret = db_session.query(Secrets).filter(Secrets.game_id == game.game_id, Secrets.acomplice == True).one()

    assert murderer_secret.player_id is not None
    assert acomplice_secret.player_id is not None
    assert murderer_secret.player_id != acomplice_secret.player_id