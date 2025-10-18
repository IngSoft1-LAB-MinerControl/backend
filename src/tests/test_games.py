"""
Tests for the Game endpoints and services, refactored to use Pytest fixtures.
"""
import datetime
from unittest.mock import patch
import pytest

# Nota: Ya no son necesarias las importaciones de sqlalchemy, TestClient, etc.,
# ya que la configuración está centralizada en conftest.py.
from src.database.models import Game, Player

# --- Test cases for Game creation ---
def test_create_game_success(client):
    """Verifica que se puede crear una partida con datos válidos."""
    # El status "waiting players" es el default, no es necesario enviarlo.
    game_data = {"name": "New Game", "max_players": 6, "min_players": 2, "status" : "waiting players"}
    response = client.post("/games", json=game_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Game"
    assert data["max_players"] == 6
    assert data["min_players"] == 2
    assert data["status"] == "waiting players"
    assert data["players_amount"] == 0

def test_create_game_invalid_input(client):
    """Verifica que la API rechaza datos de entrada inválidos."""
    game_data = {"name": "Invalid Game", "max_players": "invalid", "min_players": 2}
    response = client.post("/games", json=game_data)
    assert response.status_code == 422

# --- Test cases for listing available games ---
def test_list_available_games_success(client, db_session):
    """Verifica que la API lista correctamente solo las partidas 'waiting' y 'bootable'."""
    # Arrange: Crear datos de prueba directamente en la DB para un control preciso de los estados
    game1 = Game(name="Game 1", status="waiting players", max_players=4, min_players=2, players_amount=1)
    game2 = Game(name="Game 2", status="bootable", max_players=4, min_players=2, players_amount=2)
    game3 = Game(name="Game 3", status="in course", max_players=4, min_players=2, players_amount=2)
    game4 = Game(name="Game 4", status="finished", max_players=4, min_players=2, players_amount=2)
    db_session.add_all([game1, game2, game3, game4])
    db_session.commit()

    # Act
    response = client.get("/games/availables")
    assert response.status_code == 200
    games = response.json()
    
    # Assert
    game_names = {g['name'] for g in games}
    assert len(games) == 2
    assert "Game 1" in game_names
    assert "Game 2" in game_names
    assert "Game 3" not in game_names
    assert "Game 4" not in game_names

# --- Test cases for deleting a game ---
def test_delete_game_success(client):
    """Verifica que una partida puede ser borrada exitosamente."""
    # Arrange: Crear la partida a través de la API
    create_resp = client.post("/games", json={"name": "Game to Delete", "max_players": 4, "min_players": 2, "status" : "waiting players"})
    game_id = create_resp.json()["game_id"]

    # Act
    delete_resp = client.delete(f"/game/{game_id}")
    assert delete_resp.status_code == 204

    # Assert: Confirmar que ya no existe
    get_resp = client.get(f"/games/{game_id}")
    assert get_resp.status_code == 404

def test_delete_game_not_found(client):
    """Verifica el borrado de una partida inexistente."""
    response = client.delete("/game/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"

# --- Test cases for getting a game by ID ---
def test_get_game_success(client):
    """Verifica que se puede obtener una partida por su ID."""
    # Arrange
    create_resp = client.post("/games", json={"name": "Test Game", "max_players": 4, "min_players": 2, "status" : "waiting players"})
    game_id = create_resp.json()["game_id"]
    
    # Act & Assert
    response = client.get(f"/games/{game_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Game"
    assert data["game_id"] == game_id

def test_get_game_not_found(client):
    """Verifica la obtención de una partida inexistente."""
    response = client.get("/games/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"

# --- Test cases for initializing a game ---
@patch('src.database.services.services_cards.init_detective_cards')
@patch('src.database.services.services_cards.init_event_cards')
@patch('src.database.services.services_secrets.init_secrets')
@patch('src.database.services.services_cards.deal_NSF')
@patch('src.database.services.services_cards.deal_cards_to_players')
@patch('src.database.services.services_secrets.deal_secrets_to_players')
@patch('src.database.services.services_cards.setup_initial_draft_pile')
def test_initialize_game_success(mock_setup_draft, mock_deal_secrets, mock_deal_cards, mock_deal_nsf, mock_init_secrets, mock_init_events, mock_init_detectives,db_session ,client):
    """Verifica que una partida 'bootable' puede ser inicializada."""
    """Verifica que una partida 'bootable' puede ser inicializada."""
    # Arrange: Crear una partida y jugadores directamente en la DB para un control total
    game = Game(
        name="Test Game", 
        status="waiting players", 
        max_players=4, 
        min_players=2, 
        players_amount=2
    )
    db_session.add(game)
    db_session.commit()
    db_session.refresh(game)
    
    player1 = Player(name="Player 1", game_id=game.game_id, birth_date=datetime.date(2000, 1, 1))
    player2 = Player(name="Player 2", game_id=game.game_id, birth_date=datetime.date(2000, 1, 1))
    db_session.add_all([player1, player2])
    db_session.commit()

    # Act
    response = client.post(f"/game/beginning/{game.game_id}")
    
    # Assert
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "in course"

def test_initialize_game_not_found(client):
    """Verifica el inicio de una partida inexistente."""
    response = client.post("/game/beginning/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"

def test_initialize_game_already_started(client, db_session):
    """Verifica que una partida 'in course' no puede ser re-inicializada."""
    # Arrange: Crear una partida directamente en DB con el estado deseado
    game = Game(name="Test Game", status="in course", max_players=4, min_players=2, players_amount=2)
    db_session.add(game)
    db_session.commit()
    
    response = client.post(f"/game/beginning/{game.game_id}")
    assert response.status_code == 400
    assert response.json()["detail"] == "Game already started"

def test_initialize_game_not_enough_players(client):
    """Verifica que una partida no puede iniciar sin suficientes jugadores."""
    # Arrange
    game_resp = client.post("/games", json={"name": "Test Game", "max_players": 4, "min_players": 2, "status" : "waiting players"})
    game_id = game_resp.json()["game_id"]
    client.post(f"/player?player_name=Player 1&game_id={game_id}&birth_date=2000-01-01") # Solo 1 jugador

    # Act & Assert
    response = client.post(f"/game/beginning/{game_id}")
    assert response.status_code == 424
    assert response.json()["detail"] == "Error, you need more players to start game"

# --- Test cases for updating the turn ---
def test_update_turn_success(client, db_session):
    """Verifica que el turno avanza al siguiente jugador."""
    # Arrange
    game = Game(name="Test Game", status="in course", max_players=4, min_players=2, players_amount=2, current_turn=1)
    db_session.add(game)
    db_session.commit()
    game_id = game.game_id

    # Act
    response = client.put(f"/game/update_turn/{game_id}")
    
    # Assert
    assert response.status_code == 202
    assert response.json() == 2
    updated_game = db_session.query(Game).get(game_id)
    assert updated_game.current_turn == 2

def test_update_turn_game_not_found(client):
    """Verifica la actualización de turno de una partida inexistente."""
    response = client.put("/game/update_turn/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"

def test_update_turn_wraps_around(client, db_session):
    """Verifica que el turno se reinicia al primer jugador después del último."""
    # Arrange
    game = Game(name="Test Game", status="in course", max_players=2, min_players=2, players_amount=2, current_turn=2)
    db_session.add(game)
    db_session.commit()
    
    # Act
    response = client.put(f"/game/update_turn/{game.game_id}")
    
    # Assert
    assert response.status_code == 202
    assert response.json() == 1

# --- Test cases for service functions (Unit/Integration) ---
def test_assign_turn_to_players_success(db_session):
    """Verifica que el servicio 'assign_turn_to_players' asigna órdenes de turno únicos."""
    from src.database.services.services_games import assign_turn_to_players
    
    # Arrange
    game = Game(name="Test Game", max_players=4, min_players=2, players_amount=2)
    player1 = Player(name="Player 1", host=True, game=game, birth_date=datetime.date(2000, 1, 1))
    player2 = Player(name="Player 2", host=False, game=game, birth_date=datetime.date(2000, 2, 1))
    db_session.add_all([game, player1, player2])
    db_session.commit()

    # Act
    assign_turn_to_players(game.game_id, db_session)

    # Assert
    db_session.refresh(player1)
    db_session.refresh(player2)
    assert {player1.turn_order, player2.turn_order} == {1, 2}

def test_update_players_on_game_success(db_session):
    """Verifica que 'update_players_on_game' actualiza el contador de jugadores."""
    from src.database.services.services_games import update_players_on_game
    
    # Arrange
    game = Game(name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=0)
    player = Player(name="Player 1", host=True, game=game, birth_date=datetime.date(2000, 1, 1))
    db_session.add_all([game, player])
    db_session.commit()
    
    # Act
    update_players_on_game(game.game_id, db_session)

    # Assert
    db_session.refresh(game)
    assert game.players_amount == 1

# --- Test cases for finish_game (Service) ---
@pytest.mark.asyncio
async def test_finish_game_success(db_session):
    """Verifica que el servicio 'finish_game' cambia el estado de la partida."""
    from src.database.services.services_games import finish_game
    
    # Arrange
    game = Game(name="Test Game", status="in course", max_players=4, min_players=2, players_amount=2)
    db_session.add(game)
    db_session.commit()
    
    # Act
    result = await finish_game(game.game_id, db_session)
    
    # Assert
    assert result == {"message": f"Game {game.game_id} finished successfully."}
    db_session.refresh(game)
    assert game.status == "finished"

@pytest.mark.asyncio
async def test_finish_game_already_finished(db_session):
    """Verifica el comportamiento de 'finish_game' en una partida ya finalizada."""
    from src.database.services.services_games import finish_game
    
    # Arrange
    game = Game(name="Test Game", status="finished", max_players=4, min_players=2, players_amount=2)
    db_session.add(game)
    db_session.commit()
    
    # Act
    result = await finish_game(game.game_id, db_session)
    
    # Assert
    assert result == {"message": f"Game {game.game_id} is already finished."}

# --- New Exhaustive Tests (ya refactorizados) ---
def test_update_players_on_game_changes_status_to_bootable(db_session):
    """Verifica que el estado cambia a 'bootable' cuando se alcanza el mínimo de jugadores."""
    from src.database.services.services_games import update_players_on_game
    
    # Arrange
    game = Game(name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=1)
    player1 = Player(name="Player 1", host=True, game=game, birth_date=datetime.date(2000, 1, 1))
    player2 = Player(name="Player 2", host=False, game=game, birth_date=datetime.date(2001, 1, 1))
    db_session.add_all([game, player1, player2])
    db_session.commit()
    
    # Act
    update_players_on_game(game.game_id, db_session)

    # Assert
    db_session.refresh(game)
    assert game.players_amount == 2
    assert game.status == "bootable"

def test_update_players_on_game_changes_status_to_full(db_session):
    """Verifica que el estado cambia a 'Full' cuando se alcanza el máximo de jugadores."""
    from src.database.services.services_games import update_players_on_game
    
    # Arrange
    game = Game(name="Test Game", status="bootable", max_players=2, min_players=2, players_amount=1)
    player1 = Player(name="Player 1", host=True, game=game, birth_date=datetime.date(2000, 1, 1))
    player2 = Player(name="Player 2", host=False, game=game, birth_date=datetime.date(2001, 1, 1))
    db_session.add_all([game, player1, player2])
    db_session.commit()
    
    # Act
    update_players_on_game(game.game_id, db_session)

    # Assert
    db_session.refresh(game)
    assert game.players_amount == 2
    assert game.status == "Full"

@pytest.mark.asyncio
async def test_finish_game_not_found(db_session):
    """Verifica que 'finish_game' maneja el caso de una partida no encontrada."""
    from src.database.services.services_games import finish_game
    
    # Act & Assert
    with pytest.raises(Exception): # Idealmente, una excepción más específica si tu servicio la lanza
        await finish_game(999, db_session)