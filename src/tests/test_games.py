"""
Exhaustive tests for the Game endpoints and services, using pytest fixtures for isolation.
"""
import datetime
import pytest
from unittest.mock import patch, AsyncMock

from src.database.models import Game, Player
from src.database.services.services_games import assign_turn_to_players, update_players_on_game, finish_game

# --- Tests for Game Creation (POST /games) ---

@pytest.mark.asyncio
async def test_create_game_success(client, mocker):
    """Verifies that a game can be created with valid data."""
    mock_broadcast = mocker.patch('src.routes.games_routes.broadcast_available_games', new_callable=AsyncMock)
    game_data = {"name": "New Game", "max_players": 6, "min_players": 2, "status": "waiting players"}
    
    response = client.post("/games", json=game_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Game"
    assert data["max_players"] == 6
    assert data["min_players"] == 2
    assert data["status"] == "waiting players"
    assert data["players_amount"] == 0
    mock_broadcast.assert_awaited_once()

@pytest.mark.asyncio
async def test_create_game_invalid_input(client):
    """Verifies that the API rejects invalid input data (e.g., wrong type)."""
    game_data = {"name": "Invalid Game", "max_players": "six", "min_players": "two"}
    response = client.post("/games", json=game_data)
    assert response.status_code == 422


# --- Tests for Listing Games ---

def test_list_all_games(client, db_session):
    """Verifies that GET /games returns all created games."""
    db_session.add_all([
        Game(name="Game 1", status="waiting players", max_players=4, min_players=2, players_amount=2),
        Game(name="Game 2", status="in course", max_players=4, min_players=2, players_amount=4)
    ])
    db_session.commit()

    response = client.get("/games")
    assert response.status_code == 200
    assert len(response.json()) == 2

def test_list_available_games_success(client, db_session):
    """Verifies that GET /games/availables only returns 'waiting' and 'bootable' games."""
    db_session.add_all([
        Game(name="Waiting Game", status="waiting players", max_players=4, min_players=2, players_amount=0),
        Game(name="Bootable Game", status="bootable", max_players=4, min_players=2, players_amount=4),
        Game(name="In Course Game", status="in course", max_players=4, min_players=2, players_amount=2),
        Game(name="Finished Game", status="finished", max_players=4, min_players=2, players_amount=2)
    ])
    db_session.commit()

    response = client.get("/games/availables")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    game_names = {g['name'] for g in data}
    assert "Waiting Game" in game_names
    assert "Bootable Game" in game_names

def test_list_available_games_empty(client):
    """Verifies an empty list is returned when no games are available."""
    response = client.get("/games/availables")
    assert response.status_code == 200
    assert response.json() == []


# --- Tests for Getting a Single Game (GET /games/{game_id}) ---

def test_get_game_success(client, db_session):
    """Verifies that a single game can be retrieved by its ID."""
    game = Game(name="Test Game", max_players=4, min_players=2, players_amount=2)
    db_session.add(game)
    db_session.commit()

    response = client.get(f"/games/{game.game_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Game"
    assert data["game_id"] == game.game_id

def test_get_game_not_found(client):
    """Verifies a 404 is returned for a non-existent game ID."""
    response = client.get("/games/999")
    assert response.status_code == 404


# --- Tests for Deleting a Game (DELETE /game/{game_id}) ---

@pytest.mark.asyncio
async def test_delete_game_success(client, db_session, mocker):
    """Verifies a game can be successfully deleted."""
    mock_broadcast = mocker.patch('src.routes.games_routes.broadcast_available_games', new_callable=AsyncMock)
    game = Game(name="Game to Delete", max_players=4, min_players=2, players_amount=2)
    db_session.add(game)
    db_session.commit()

    delete_resp = client.delete(f"/game/{game.game_id}")
    assert delete_resp.status_code == 204
    mock_broadcast.assert_awaited_once()

    get_resp = client.get(f"/games/{game.game_id}")
    assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_game_not_found(client):
    """Verifies a 404 is returned when trying to delete a non-existent game."""
    response = client.delete("/game/999")
    assert response.status_code == 404


# --- Tests for Initializing a Game (POST /game/beginning/{game_id}) ---

@patch('src.routes.games_routes.setup_initial_draft_pile')
@patch('src.routes.games_routes.deal_secrets_to_players')
@patch('src.routes.games_routes.deal_cards_to_players')
@patch('src.routes.games_routes.deal_NSF')
@patch('src.routes.games_routes.init_secrets')
@patch('src.routes.games_routes.init_event_cards')
@patch('src.routes.games_routes.init_detective_cards')
@patch('src.routes.games_routes.assign_turn_to_players')
@pytest.mark.asyncio
async def test_initialize_game_success(mock_assign_turns, mock_init_detectives, mock_init_events, mock_init_secrets, mock_deal_nsf, mock_deal_cards, mock_deal_secrets, mock_setup_draft, client, db_session, mocker):
    """Verifies a 'bootable' game can be initialized and all setup services are called."""
    mock_broadcast_game = mocker.patch('src.routes.games_routes.broadcast_game_information', new_callable=AsyncMock)
    mock_broadcast_avail = mocker.patch('src.routes.games_routes.broadcast_available_games', new_callable=AsyncMock)
    
    game = Game(name="Test Game", status="bootable", max_players=4, min_players=2, players_amount=2)
    db_session.add(game)
    db_session.commit()

    response = client.post(f"/game/beginning/{game.game_id}")
    
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "in course"
    
    # Verify all initialization services were called
    mock_assign_turns.assert_called_once()
    mock_init_detectives.assert_called_once()
    mock_init_events.assert_called_once()
    mock_init_secrets.assert_called_once()
    mock_deal_nsf.assert_called_once()
    mock_deal_cards.assert_called_once()
    mock_deal_secrets.assert_called_once()
    mock_setup_draft.assert_called_once()
    mock_broadcast_game.assert_awaited_once()
    mock_broadcast_avail.assert_awaited_once()

@pytest.mark.asyncio
async def test_initialize_game_not_found(client):
    """Verifies a 404 for initializing a non-existent game."""
    response = client.post("/game/beginning/999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_initialize_game_already_started(client, db_session):
    """Verifies a 400 if the game is already 'in course'."""
    game = Game(name="In Course Game", status="in course", max_players=4, min_players=2, players_amount=2)
    db_session.add(game)
    db_session.commit()
    
    response = client.post(f"/game/beginning/{game.game_id}")
    assert response.status_code == 400
    assert "Game already started" in response.json()["detail"]

@pytest.mark.asyncio
async def test_initialize_game_not_enough_players(client, db_session):
    """Verifies a 424 if there are not enough players to start."""
    game = Game(name="Not Enough Players", status="waiting players", max_players=4, min_players=2, players_amount=1)
    db_session.add(game)
    db_session.commit()

    response = client.post(f"/game/beginning/{game.game_id}")
    assert response.status_code == 424
    assert "need more players" in response.json()["detail"]


# --- Tests for Updating Turn (PUT /game/update_turn/{game_id}) ---

@pytest.mark.asyncio
async def test_update_turn_success(client, db_session, mocker):
    """Verifies the turn advances to the next player."""
    mock_broadcast = mocker.patch('src.routes.games_routes.broadcast_game_information', new_callable=AsyncMock)
    game = Game(name="Test Game", status="in course", max_players=4, min_players=2, players_amount=2, current_turn=1)
    db_session.add(game)
    db_session.commit()

    response = client.put(f"/game/update_turn/{game.game_id}")
    
    assert response.status_code == 202
    assert response.json() == 2
    mock_broadcast.assert_awaited_once_with(game.game_id)

@pytest.mark.asyncio
async def test_update_turn_wraps_around(client, db_session, mocker):
    """Verifies the turn wraps around from the last player to the first."""
    mock_broadcast = mocker.patch('src.routes.games_routes.broadcast_game_information', new_callable=AsyncMock)
    game = Game(name="Test Game", status="in course", max_players=2, min_players=2, players_amount=2, current_turn=2)
    db_session.add(game)
    db_session.commit()
    
    response = client.put(f"/game/update_turn/{game.game_id}")
    
    assert response.status_code == 202
    assert response.json() == 1
    mock_broadcast.assert_awaited_once_with(game.game_id)

@pytest.mark.asyncio
async def test_update_turn_game_not_found(client):
    """Verifies a 404 for updating the turn of a non-existent game."""
    response = client.put("/game/update_turn/999")
    assert response.status_code == 404


# --- Tests for Service Layer Functions ---

def test_update_players_on_game_success(db_session):
    """Verifies 'update_players_on_game' correctly increments the player count."""
    game = Game(name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=0)
    db_session.add(game)
    db_session.commit()
    
    update_players_on_game(game.game_id, db_session)

    db_session.refresh(game)
    assert game.players_amount == 1
    assert game.status == "waiting players"

def test_update_players_on_game_changes_status_to_bootable(db_session):
    """Verifies the game status changes to 'bootable' when min_players is reached."""
    game = Game(name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=1)
    db_session.add(game)
    db_session.commit()
    
    update_players_on_game(game.game_id, db_session)

    db_session.refresh(game)
    assert game.players_amount == 2
    assert game.status == "bootable"

def test_update_players_on_game_changes_status_to_full(db_session):
    """Verifies the game status changes to 'Full' when max_players is reached."""
    game = Game(name="Test Game", status="bootable", max_players=2, min_players=2, players_amount=1)
    db_session.add(game)
    db_session.commit()
    
    update_players_on_game(game.game_id, db_session)

    db_session.refresh(game)
    assert game.players_amount == 2
    assert game.status == "Full"

def test_assign_turn_to_players_success(db_session):
    """Verifies 'assign_turn_to_players' assigns unique, ordered turns based on birth date."""
    game = Game(name="Turn Test", max_players=4, min_players=2, players_amount = 3)
    # Birthdays are chosen to be clearly distinct distances from Sept 15
    player_closest = Player(name="Closest", game=game, birth_date=datetime.date(2000, 9, 14)) # 1 day away
    player_farthest = Player(name="Farthest", game=game, birth_date=datetime.date(2000, 3, 15)) # ~184 days away
    player_middle = Player(name="Middle", game=game, birth_date=datetime.date(2000, 8, 1)) # ~45 days away
    db_session.add_all([game, player_closest, player_farthest, player_middle])
    db_session.commit()

    assign_turn_to_players(game.game_id, db_session)

    db_session.refresh(player_closest)
    db_session.refresh(player_middle)
    db_session.refresh(player_farthest)
    
    assert player_closest.turn_order == 1
    assert player_middle.turn_order == 2
    assert player_farthest.turn_order == 3
    
    db_session.refresh(game)
    assert game.current_turn == 1

@pytest.mark.asyncio
async def test_finish_game_success(db_session, mocker):
    """Verifies 'finish_game' service correctly changes the game status."""
    mock_broadcast = mocker.patch('src.database.services.services_games.broadcast_game_information', new_callable=AsyncMock)
    game = Game(name="Game to Finish", status="in course", max_players=4, min_players=2, players_amount=2)
    db_session.add(game)
    db_session.commit()
    
    result = await finish_game(game.game_id, db_session)
    
    assert result == {"message": f"Game {game.game_id} finished successfully."}
    db_session.refresh(game)
    assert game.status == "finished"
    mock_broadcast.assert_awaited_once_with(game.game_id)

@pytest.mark.asyncio
async def test_finish_game_already_finished(db_session):
    """Verifies 'finish_game' returns the correct message for an already finished game."""
    game = Game(name="Already Finished", status="finished", max_players=4, min_players=2, players_amount=2)
    db_session.add(game)
    db_session.commit()
    
    result = await finish_game(game.game_id, db_session)
    
    assert result == {"message": f"Game {game.game_id} is already finished."}