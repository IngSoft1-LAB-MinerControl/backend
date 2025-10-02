
import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Game, Player, Card, Secrets
from src.database.database import get_db
from fastapi.testclient import TestClient
from src.main import app

# Usar SQLite en disco temporal para persistencia entre requests
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

with TestingSessionLocal() as db:
    db.query(Secrets).delete()
    db.query(Card).delete()
    db.query(Player).delete()
    db.query(Game).delete() # Tiene que ser la última por las relaciones (foreign keys)
    db.commit()
    
    game_1 = Game(game_id=1, name="Oso's Lobby", status="waiting players", max_players=6, min_players=2, players_amount=1)
    player_1 = Player(player_id=1, name="Luca", host=True, birth_date=datetime.date(2000, 1, 1), turn_order=1, game_id=1)
    card_1 = Card(card_id=1, type="Generic Card", picked_up=False, dropped=False, player_id=1 , game_id=1)
    secret_1 = Secrets(secret_id=1, murderer=True, acomplice=False, revelated=False, player_id=1, game_id=1)
    g2 = Game(game_id=2, name="Angelo's Lobby", status="bootable", max_players=6, min_players=2, players_amount=2)
    g3 = Game(game_id=3, name="Goat's Lobby", status="Full", max_players=2, min_players=2, players_amount=2)
    player_2_1 = Player(player_id=2, name="Luca", host=True, birth_date=datetime.date(2000, 1, 1), turn_order=2, game_id=2)
    player_2_2 = Player(player_id=3, name="Angelo", host=False, birth_date=datetime.date(2000, 9, 15), turn_order=1, game_id=2)
    player_3_1 = Player(player_id=4, name="Luca", host=True, birth_date=datetime.date(2000, 1, 1), turn_order=2, game_id=3)
    player_3_2 = Player(player_id=5, name="Angelo", host=False, birth_date=datetime.date(2000, 9, 15), turn_order=1, game_id=3)
    
    db.add(game_1)
    db.add(g2)
    db.add(g3)
    db.add(player_1)
    db.add(player_2_1)
    db.add(player_2_2)
    db.add(player_3_1)
    db.add(player_3_2)
    db.add(card_1)
    db.add (secret_1)
    db.commit()

def test_create_games () : 
    parameters = {"max_players" : 6, "min_players" : 2, "status" :  "Full", "name" : "Luca's Lobby"}
    response = client.post(
        "/games", json = parameters)
    assert response.status_code == 201
    data = response.json() 
    assert data["max_players"] == 6
    assert data["min_players"] == 2
    assert data["status"] == "Full"
    assert data["name"] == "Luca's Lobby"
    


def test_create_games_with_parameters_missing():
    parameters = {"max_players" : 6, "min_players" : 2, "status" :  "waiting players", "" : ""}
    response = client.post(
        "/games", json = parameters)
    assert response.status_code == 422


def test_list_available_games():
    
    response = client.get("/games/availables")
    assert response.status_code == 200

    data = response.json()
    assert data[0]["status"] == "waiting players"
    assert data[1]["status"] == "bootable"
    print (data)  
    assert len(data) == 2


def test_delete_game(): 
    parameters = {"max_players" : 6, "min_players" : 2, "status" :  "waiting players", "name" : "Luca's Lobby 2"}
    create_response = client.post (
        "/games", json = parameters)
    
    assert create_response.status_code == 201
    game = create_response.json()
    game_id = game["game_id"]
    response = client.delete(f"/game/{game_id}" )
    assert response.status_code == 204

def test_initialize_game() : #Voy a inicializr el g3 que defini arriba
    response = client.post(f"/game/beginning/{3}")
    assert response.status_code == 202 
    data = response.json()
    assert data["current_turn"] == 1 
    response_cards = client.get(f"lobby/cards/{3}")
    assert response_cards.status_code == 200
    data_cards = response_cards.json()
    assert 61 == len(data_cards)
    response_players = client.get(f"lobby/players/{3}")
    assert response_players.status_code == 200
    data_players = response_players.json()
    assert len(data_players) == 2
    player_id_test = data_players[0]["player_id"] 
    response_secrets = client.get (f"lobby/secrets/{player_id_test}")
    assert response_secrets.status_code == 200
    data_secrets = response_secrets.json()
    assert 3 == len(data_secrets)
    assert data_players[0]["turn_order"] == 2
    assert data_players[1]["turn_order"] == 1

    
def test_update_turn() : #El current turn del game 3 esta seteado en 1, por lo tanto quiero que se actualice a 2 
    response = client.put(f"/game/update_turn/{3}")
    assert response.status_code == 202
    data = response.json()
    assert data == 2 

def test_update_turn_from_last_player_to_first() : #game 3 tiene 2 jugadores, y el current turn esta en 2, 
                                                    #por lo tanto el proximo debe ser 1
    response = client.put(f"/game/update_turn/{3}")
    assert response.status_code == 202
    data = response.json()
    assert data == 1




