"""
Exhaustive tests for the Player endpoints, using pytest fixtures for isolation.
"""
import datetime
import pytest
from unittest.mock import patch, AsyncMock

from src.database.models import Game, Player

# --- Tests for Player Creation (POST /players) ---

def test_create_player_success(client, db_session):
    """
    Verifies that a player can be successfully created and added to an available game.
    """
    # Arrange: Create a game that is waiting for players
    game = Game(name="Waiting Game", status="waiting players", max_players=4, min_players=2, players_amount=0)
    db_session.add(game)
    db_session.commit()
    db_session.refresh(game)
    game_id = game.game_id

    player_data = {"name": "New Player", "host": True, "game_id": game_id, "birth_date": "2000-01-01"}

    # Act
    response = client.post("/players", json=player_data)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Player"
    assert data["host"] is True
    assert data["game_id"] == game_id
    assert "player_id" in data

    # Verify the player was actually added to the database
    player_in_db = db_session.query(Player).filter(Player.player_id == data["player_id"]).one()
    assert player_in_db.name == "New Player"

    # Verify the game's player count was updated by the service
    game_in_db = db_session.query(Game).filter(Game.game_id == game_id).one()
    
    assert game_in_db.players_amount == 1

def test_create_player_game_not_found(client):
    """
    Verifies that creating a player for a non-existent game returns a 404 error.
    """
    player_data = {"name": "Lost Player", "host": False, "game_id": 999, "birth_date": "2000-01-01"}
    
    response = client.post("/players", json=player_data)
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"

def test_create_player_game_full(client, db_session):
    """
    Verifies that trying to join a full game returns a 400 error.
    """
    # Arrange: Create a game that is already full
    game = Game(name="Full Game", status="Full", max_players=2, min_players=2, players_amount=2)
    db_session.add(game)
    db_session.commit()

    player_data = {"name": "Late Player", "host": False, "game_id": game.game_id, "birth_date": "2000-01-01"}

    # Act
    response = client.post("/players", json=player_data)

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Game already full"

def test_create_player_invalid_data(client, db_session):
    """
    Verifies that creating a player with invalid data (e.g., missing fields) returns a 422 error.
    """
    game = Game(name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=0)
    db_session.add(game)
    db_session.commit()

    # Missing 'name' and 'birth_date'
    invalid_player_data = {"host": True, "game_id": game.game_id}
    
    response = client.post("/players", json=invalid_player_data)
    
    assert response.status_code == 422


# --- Tests for Listing Players (GET /lobby/players/{game_id}) ---

def test_list_players_success(client, db_session):
    """
    Verifies that all players for a given game are listed correctly.
    """
    # Arrange: Create a game and add multiple players to it
    game = Game(name="Popular Game", status="waiting players", max_players=4, min_players=2, players_amount=2)
    player1 = Player(name="Player One", game=game, host=True, birth_date=datetime.date(2000, 1, 1))
    player2 = Player(name="Player Two", game=game, host=False, birth_date=datetime.date(2001, 1, 1))
    db_session.add_all([game, player1, player2])
    db_session.commit()

    # Act
    response = client.get(f"/lobby/players/{game.game_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    player_names = {p['name'] for p in data}
    assert "Player One" in player_names
    assert "Player Two" in player_names

def test_list_players_game_not_found(client):
    """
    Verifies that listing players for a non-existent game returns a 404 error.
    """
    response = client.get("/lobby/players/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "game not found or no players in this game"

def test_list_players_game_with_no_players(client, db_session):
    """
    Verifies that listing players for an existing but empty game returns a 404 error.
    """
    # Arrange: Create a game with no players
    game = Game(name="Empty Game", status="waiting players", max_players=4, min_players=2, players_amount=0)
    db_session.add(game)
    db_session.commit()

    # Act
    response = client.get(f"/lobby/players/{game.game_id}")

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "game not found or no players in this game"


# --- Tests for Deleting a Player (DELETE /players/{player_id}) ---

def test_delete_player_success(client, db_session):
    """
    Verifies that a player can be successfully deleted.
    """
    # Arrange: Create a game and a player to delete
    game = Game(name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=2)
    player_to_delete = Player(name="Leaver", game=game, host=False, birth_date=datetime.date(2000, 1, 1))
    db_session.add_all([game, player_to_delete])
    db_session.commit()
    player_id = player_to_delete.player_id

    # Act
    delete_response = client.delete(f"/players/{player_id}")

    # Assert
    assert delete_response.status_code == 204

    # Verify the player is gone from the database
    player_in_db = db_session.query(Player).filter(Player.player_id == player_id).first()
    assert player_in_db is None

def test_delete_player_not_found(client):
    """
    Verifies that trying to delete a non-existent player returns a 404 error.
    """
    response = client.delete("/players/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Player not found"