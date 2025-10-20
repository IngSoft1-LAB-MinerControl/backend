import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Game, Player
from src.database.database import get_db
from fastapi.testclient import TestClient
from src.main import app

# Configuración de la base de datos de prueba para jugadores
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_players.db"
if os.path.exists("./test_players.db"):
    os.remove("./test_players.db")
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

# Poblar la base de datos con datos de ejemplo para diferentes escenarios
with TestingSessionLocal() as db:
    # Escenario 1: Partida normal con un jugador
    game1 = Game(game_id=1, name="Test Game", status="waiting players", max_players=4, min_players=2, players_amount=1)
    player1 = Player(player_id=1, name="Test Player", host=True, birth_date=datetime.date(2000, 1, 1), game_id=1)
    db.add(game1)
    db.add(player1)

    # Escenario 2: Partida llena
    game2 = Game(game_id=2, name="Full Game", status="Full", max_players=2, min_players=2, players_amount=2)
    player2 = Player(player_id=2, name="Player A", host=True, birth_date=datetime.date(2000, 1, 1), game_id=2)
    player3 = Player(player_id=3, name="Player B", host=False, birth_date=datetime.date(2001, 1, 1), game_id=2)
    db.add(game2)
    db.add(player2)
    db.add(player3)

    # Escenario 3: Partida válida pero sin jugadores
    game3 = Game(game_id=3, name="Empty Game", status="waiting players", max_players=4, min_players=2, players_amount=0)
    db.add(game3)
    
    game4 = Game(game_id = 4, name = "Delete Game", status = "waiting players", max_players = 4, min_players = 2, players_amount = 0)
    db.add(game4)
    db.commit()

def test_create_player_success():
    response = client.post(
        "/players",
        json={"name": "New Player", "host": False, "game_id": 1, "birth_date": "2001-05-10"}
    )
    assert response.status_code == 201
    player_id = response.json()
    assert isinstance(player_id, int)

def test_create_player_game_not_found():
    response = client.post(
        "/players",
        json={"name": "Another Player", "host": False, "game_id": 999, "birth_date": "2002-06-11"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found"

def test_create_player_game_full():
    game_response = client.post("/games",
                    json ={"name" : "GameTestsss", "status" : "full", "max_players" : 2, "min_players" : 2} )
    game_id = game_response.json()["game_id"]
    mock_player = client.post(
        "/players",
        json={"name": "Mock Player 1", "host": False, "game_id": game_id, "birth_date": "2004-08-13"}
    )
    mock_player2 = client.post(
        "/players",
        json={"name": "Mock Player 2", "host": False, "game_id": game_id, "birth_date": "2004-08-13"}
    )

    response = client.post(
        "/players",
        json={"name": "Extra Player", "host": False, "game_id": game_id, "birth_date": "2004-08-13"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Game already full"

def test_create_player_success():
    game_response = client.post("/games",
                    json ={"name" : "GameTestsss", "status" : "waiting players", "max_players" : 6, "min_players" : 2} )
    game_id = game_response.json()["game_id"]
    
    response = client.post(
        "/players",
        json={"name": "New Player", "host": False, "game_id": game_id, "birth_date": "2001-05-10"}
    )
    assert response.status_code == 201
    data = response.json()
    # Verificamos que la respuesta sea un diccionario y que contenga el ID del jugador
    assert isinstance(data, dict)
    assert "player_id" in data

def test_list_players_for_empty_game():
    response = client.get("/lobby/players/3")
    assert response.status_code == 404
    assert response.json()["detail"] == "game not found or no players in this game"

def test_list_players_game_not_found():
    response = client.get("/lobby/players/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "game not found or no players in this game"

def test_delete_player_success():
    game_response = client.post("/games",
                    json ={"name" : "GameTestsss", "status" : "waiting players", "max_players" : 6, "min_players" : 2} )
    game_id = game_response.json()["game_id"]
    
    create_response = client.post(
        "/players",
        json={"name": "PlayerToDelete", "host": False, "game_id": game_id, "birth_date": "2003-07-12"}
    )
    if create_response.status_code != 201:
        print("DEBUG - Mensaje de error de la API:", create_response.json())
    
    player_id = create_response.json()["player_id"]

    delete_response = client.delete(f"/players/{player_id}")
    assert delete_response.status_code == 204

def test_delete_player_not_found():
    response = client.delete("/players/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Player not found"