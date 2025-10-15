import datetime
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Game, Player, Detective, Set
from src.database.database import get_db
from fastapi.testclient import TestClient
from src.main import app

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_sets.db"
if os.path.exists("./test_sets.db"):
    os.remove("./test_sets.db")
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

def setup_players_and_detectives():
    with TestingSessionLocal() as db:
        db.query(Set).delete()
        db.query(Detective).delete()
        db.query(Player).delete()
        db.query(Game).delete()
        db.commit()
        game = Game(game_id=1, name="Test Game", status="esperando jugadores", max_players=6, min_players=2, players_amount=2)
        player1 = Player(player_id=1, name="Player1", host=True, birth_date=datetime.date(2000, 1, 1), turn_order=1, game_id=1)
        player2 = Player(player_id=2, name="Player2", host=False, birth_date=datetime.date(2000, 1, 2), turn_order=2, game_id=1)
        db.add_all([game, player1, player2])
        db.commit()
        # Detectives para sets de 2
        d1 = Detective(card_id=1, type="detective", name="Adriane Oliver", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=2, set_id=None)
        d2 = Detective(card_id=2, type="detective", name="Adriane Oliver", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=2, set_id=None)
        # Wildcard
        d3 = Detective(card_id=3, type="detective", name="Harley Quin Wildcard", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=2, set_id=None)
        # Detectives para sets de 3
        d4 = Detective(card_id=4, type="detective", name="Miss Marple", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=3, set_id=None)
        d5 = Detective(card_id=5, type="detective", name="Miss Marple", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=3, set_id=None)
        d6 = Detective(card_id=6, type="detective", name="Miss Marple", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=3, set_id=None)
        # Beresford brothers
        d7 = Detective(card_id=7, type="detective", name="Tommy Beresford", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=2, set_id=None)
        d8 = Detective(card_id=8, type="detective", name="Tuppence Beresford", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=2, set_id=None)
        db.add_all([d1, d2, d3, d4, d5, d6, d7, d8])
        db.commit()

def test_set_of2_same_name():
    setup_players_and_detectives()
    response = client.post("/sets_of2/1,2")
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Adriane Oliver"

def test_set_of2_with_wildcard():
    setup_players_and_detectives()
    response = client.post("/sets_of2/1,3")
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Adriane Oliver"
    response2 = client.post("/sets_of2/3,2")
    assert response2.status_code == 201
    data2 = response2.json()
    assert data2["name"] == "Adriane Oliver"

def test_set_of2_beresford_brothers():
    setup_players_and_detectives()
    response = client.post("/sets_of2/7,8")
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Beresford brothers"

def test_set_of2_invalid():
    setup_players_and_detectives()
    # No existe card_id 99
    response = client.post("/sets_of2/1,99")
    assert response.status_code == 400
    assert "Invalid card_id" in response.json()["detail"]

def test_set_of2_wrong_quantity():
    setup_players_and_detectives()
    # Usar una carta de set de 3 en set de 2
    response = client.post("/sets_of2/4,5")
    assert response.status_code == 400
    assert "You need one more detective" in response.json()["detail"]

def test_set_of2_not_compatible():
    setup_players_and_detectives()
    # Dos detectives distintos sin wildcard ni hermanos
    response = client.post("/sets_of2/1,7")
    assert response.status_code == 400
    assert "not two compatible detectives" in response.json()["detail"]

def test_set_of3_same_name():
    setup_players_and_detectives()
    response = client.post("/sets_of3/4,5,6")
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Miss Marple"

def test_set_of3_with_wildcard():
    setup_players_and_detectives()
    response = client.post("/sets_of3/3,4,5")
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Miss Marple"

def test_set_of3_invalid():
    setup_players_and_detectives()
    response = client.post("/sets_of3/4,5,99")
    assert response.status_code == 400
    assert "Invalid card_id" in response.json()["detail"]

def test_set_of3_not_compatible():
    setup_players_and_detectives()
    response = client.post("/sets_of3/1,4,7")
    assert response.status_code == 400
    assert "not three compatible detectives" in response.json()["detail"]

def test_get_set_player():
    setup_players_and_detectives()
    # Primero crear un set
    client.post("/sets_of2/1,2")
    response = client.get("/sets/list/1")
    assert response.status_code == 201
    data = response.json()
    assert data["player_id"] == 1

def test_steal_set():
    setup_players_and_detectives()
    # Crear un set para player 1
    client.post("/sets_of2/1,2")
    # Robar el set a player 2
    response = client.put("/sets/steal/1/2/1")
    assert response.status_code == 201
    data = response.json()
    assert data["player_id"] == 2