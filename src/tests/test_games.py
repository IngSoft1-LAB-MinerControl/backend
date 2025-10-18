import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Game, Player, Detective, Event
from src.database.database import get_db
from fastapi.testclient import TestClient
from src.main import app
from unittest.mock import patch
import pytest

# Configuración de la base de datos de prueba
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_games.db"
if os.path.exists("./test_games.db"):
    os.remove("./test_games.db")
test_engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
Base.metadata.create_all(bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

def setup_database():
    with TestingSessionLocal() as db:
        db.query(Event).delete()
        db.query(Detective).delete()
        db.query(Player).delete()
        db.query(Game).delete()
        db.commit()

def create_test_game(db, game_id, name, status, max_players, min_players, players_amount, current_turn=None):
    game = Game(game_id=game_id, name=name, status=status, max_players=max_players, min_players=min_players, players_amount=players_amount, current_turn=current_turn)
    db.add(game)
    db.commit()
    db.refresh(game)
    return game

def create_test_player(db, player_id, name, host, game_id, birth_date, turn_order=None):
    player = Player(player_id=player_id, name=name, host=host, game_id=game_id, birth_date=birth_date, turn_order=turn_order)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player

# --- Test cases for Game creation ---
def test_create_game_success():
    setup_database()
    game_data = {"name": "New Game", "max_players": 6, "min_players": 2, "status": "waiting players"}
    response = client.post("/games", json=game_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Game"
    assert data["max_players"] == 6
    assert data["min_players"] == 2
    assert data["status"] == "waiting players"
    assert data["players_amount"] == 0

def test_create_game_invalid_input():
    setup_database()
    game_data = {"name": "Invalid Game", "max_players": "invalid", "min_players": 2, "status": "waiting players"}
    response = client.post("/games", json=game_data)
    assert response.status_code == 422

# --- Test cases for listing available games ---
def test_list_available_games_success():
    setup_database()
    with TestingSessionLocal() as db:
        create_test_game(db, game_id=1, name="Game 1", status="waiting players", max_players=4, min_players=2, players_amount=1)
        create_test_game(db, game_id=2, name="Game 2", status="bootable", max_players=4, min_players=2, players_amount=1)
        create_test_game(db, game_id=3, name="Game 3", status="in course", max_players=4, min_players=2, players_amount=2)
        create_test_game(db, game_id=4, name="Game 4", status="finished", max_players=4, min_players=2, players_amount=2)

    response = client.get("/games/availables")
    assert response.status_code == 200
    games = response.json()
    assert len(games) >= 2
    assert any(game["name"] == "Game 1" for game in games)
    assert any(game["name"] == "Game 2" for game in games)
    assert not any(game["name"] == "Game 3" for game in games)
    assert not any(game["name"] == "Game 4" for game in games)

# --- Test cases for deleting a game ---
def test_delete_game_success():
    setup_database()
    with TestingSessionLocal() as db:
        game = create_test_game(db, game_id=1, name="Game to Delete", status="waiting players", max_players=4, min_players=2, players_amount=1)

    response = client.delete(f"/game/{game.game_id}")
    assert response.status_code == 204

    with TestingSessionLocal() as db:
        deleted_game = db.query(Game).filter(Game.game_id == game.game_id).first()
        assert deleted_game is None

def test_delete_game_not_found():
    setup_database()
    response = client.delete("/game/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"

# --- Test cases for getting a game by ID ---
def test_get_game_success():
    setup_database()
    with TestingSessionLocal() as db:
        game = create_test_game(db, game_id=1, name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=1)

    response = client.get(f"/games/{game.game_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Game"

def test_get_game_not_found():
    setup_database()
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
def test_initialize_game_success(mock_setup_initial_draft_pile, mock_deal_secrets_to_players, mock_deal_cards_to_players, mock_deal_NSF, mock_init_secrets, mock_init_event_cards, mock_init_detective_cards):
    setup_database()
    game_id = 1
    with TestingSessionLocal() as db:
        create_test_game(db, game_id=game_id, name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=2)
        create_test_player(db, player_id=1, name="Player 1", host=True, game_id=game_id, birth_date=datetime.date(2000, 1, 1))
        create_test_player(db, player_id=2, name="Player 2", host=False, game_id=game_id, birth_date=datetime.date(2000, 1, 2))

    response = client.post(f"/game/beginning/{game_id}")
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "in course"

def test_initialize_game_not_found():
    setup_database()
    response = client.post("/game/beginning/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"

def test_initialize_game_already_started():
    setup_database()
    with TestingSessionLocal() as db:
        game = create_test_game(db, game_id=1, name="Test Game", status="in course", max_players=4, min_players=2, players_amount=2)
    response = client.post(f"/game/beginning/{game.game_id}")
    assert response.status_code == 400
    assert response.json()["detail"] == "Game already started"

def test_initialize_game_not_enough_players():
    setup_database()
    with TestingSessionLocal() as db:
        game = create_test_game(db, game_id=1, name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=1)
        create_test_player(db, player_id=1, name="Player 1", host=True, game_id=game.game_id, birth_date=datetime.date(2000, 1, 1))

    response = client.post(f"/game/beginning/{1}")
    assert response.status_code == 424
    assert response.json()["detail"] == "Error, you need more players to start game"

# --- Test cases for updating the turn ---
# --- Corrected Test Cases ---

# The DetachedInstanceError occurs because the 'game' object is used after its database session is closed.
# The fix is to use the game's ID for the API call and then re-query the game in a new session to verify the changes.
def test_update_turn_success():
    setup_database()
    game_id = 1
    with TestingSessionLocal() as db:
        create_test_game(db, game_id=game_id, name="Test Game", status="in course", max_players=4, min_players=2, players_amount=2, current_turn=1)
        create_test_player(db, player_id=1, name="Player 1", host=True, game_id=game_id, birth_date=datetime.date(2000, 1, 1))
        create_test_player(db, player_id=2, name="Player 2", host=False, game_id=game_id, birth_date=datetime.date(2000, 1, 2))

    response = client.put(f"/game/update_turn/{game_id}")
    assert response.status_code == 202
    data = response.json()
    assert data == 2

    # Verify the change in the database
    with TestingSessionLocal() as db:
        game = db.query(Game).filter(Game.game_id == game_id).first()
        assert game.current_turn == 2

def test_update_turn_game_not_found():
    setup_database()
    response = client.put("/game/update_turn/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"

def test_update_turn_wraps_around():
    setup_database()
    game_id = 1
    with TestingSessionLocal() as db:
        create_test_game(db, game_id=game_id, name="Test Game", status="in course", max_players=2, min_players=2, players_amount=2, current_turn=2)
        create_test_player(db, player_id=1, name="Player 1", host=True, game_id=game_id, birth_date=datetime.date(2000, 1, 1), turn_order=1)
        create_test_player(db, player_id=2, name="Player 2", host=False, game_id=game_id, birth_date=datetime.date(2000, 1, 2), turn_order=2)

    response = client.put(f"/game/update_turn/{game_id}")
    assert response.status_code == 202
    data = response.json()
    assert data == 1

# --- Test cases for assign_turn_to_players ---
def test_assign_turn_to_players_success():
    setup_database()
    with TestingSessionLocal() as db:
        game = create_test_game(db, game_id=1, name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=2)
        player1 = create_test_player(db, player_id=1, name="Player 1", host=True, game_id=game.game_id, birth_date=datetime.date(2000, 1, 1))
        player2 = create_test_player(db, player_id=2, name="Player 2", host=False, game_id=game.game_id, birth_date=datetime.date(2000, 2, 1))

        # Call the service function directly
        from src.database.services.services_games import assign_turn_to_players
        assign_turn_to_players(game.game_id, db)

        # Refresh players to get updated turn_order
        db.refresh(player1)
        db.refresh(player2)

        assert player1.turn_order is not None
        assert player2.turn_order is not None
        assert player1.turn_order != player2.turn_order

# --- Test cases for update_players_on_game ---
def test_update_players_on_game_success():
    setup_database()
    with TestingSessionLocal() as db:
        game = create_test_game(db, game_id=1, name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=0)
        create_test_player(db, player_id=1, name="Player 1", host=True, game_id=game.game_id, birth_date=datetime.date(2000, 1, 1))
        
        from src.database.services.services_games import update_players_on_game
        update_players_on_game(game.game_id, db)

        db.refresh(game)
        assert game.players_amount == 1

def test_update_players_on_game_game_full():
    setup_database()
    with TestingSessionLocal() as db:
        game = create_test_game(db, game_id=1, name="Test Game", status="waiting players", max_players=1, min_players=1, players_amount=1)
        
        # Call the service function directly
        from src.database.services.services_games import update_players_on_game
        result = update_players_on_game(game.game_id, db)

        assert result is None

# --- Test cases for finish_game ---
@pytest.mark.asyncio
async def test_finish_game_success():
    setup_database()
    game_id = 1
    with TestingSessionLocal() as db:
        create_test_game(db, game_id=game_id, name="Test Game", status="in course", max_players=4, min_players=2, players_amount=2)

    # Use a new session for the service call, as a real request would.
    with TestingSessionLocal() as db:
        from src.database.services.services_games import finish_game
        result = await finish_game(game_id, db)
        assert result == {"message": f"Game {game_id} finished successfully."}

    # Verify the state change in a separate session.
    with TestingSessionLocal() as db:
        game = db.query(Game).get(game_id)
        assert game.status == "finished"

@pytest.mark.asyncio
async def test_finish_game_already_finished():
    setup_database()
    game_id = 1
    with TestingSessionLocal() as db:
        create_test_game(db, game_id=game_id, name="Test Game", status="finished", max_players=4, min_players=2, players_amount=2)

    with TestingSessionLocal() as db:
        from src.database.services.services_games import finish_game
        result = await finish_game(game_id, db)
        assert result == {"message": f"Game {game_id} is already finished."}


# --- New Exhaustive Tests ---

def test_update_players_on_game_changes_status_to_bootable():
    setup_database()
    with TestingSessionLocal() as db:
        game = create_test_game(db, game_id=1, name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=1)
        create_test_player(db, player_id=1, name="Player 1", host=True, game_id=game.game_id, birth_date=datetime.date(2000, 1, 1))
        
        # Add another player to meet min_players
        create_test_player(db, player_id=2, name="Player 2", host=False, game_id=game.game_id, birth_date=datetime.date(2001, 1, 1))

        from src.database.services.services_games import update_players_on_game
        update_players_on_game(game.game_id, db)

        db.refresh(game)
        assert game.players_amount == 2
        assert game.status == "bootable"

def test_update_players_on_game_changes_status_to_full():
    setup_database()
    with TestingSessionLocal() as db:
        game = create_test_game(db, game_id=1, name="Test Game", status="bootable", max_players=2, min_players=2, players_amount=1)
        create_test_player(db, player_id=1, name="Player 1", host=True, game_id=game.game_id, birth_date=datetime.date(2000, 1, 1))
        
        # Add another player to meet max_players
        create_test_player(db, player_id=2, name="Player 2", host=False, game_id=game.game_id, birth_date=datetime.date(2001, 1, 1))

        from src.database.services.services_games import update_players_on_game
        update_players_on_game(game.game_id, db)

        db.refresh(game)
        assert game.players_amount == 2
        assert game.status == "Full"

@pytest.mark.asyncio
async def test_finish_game_not_found():
    setup_database()
    with TestingSessionLocal() as db:
        from src.database.services.services_games import finish_game
        # Expecting an exception because the game doesn't exist
        with pytest.raises(Exception): # Or a more specific HTTPException if the service raises it
            await finish_game(999, db)
