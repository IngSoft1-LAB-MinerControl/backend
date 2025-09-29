import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Game, Player, Card
from src.database.database import get_db
from fastapi.testclient import TestClient
from src.main import app

# Usar SQLite en disco temporal para persistencia entre requests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"
if os.path.exists("./test.db"):
    os.remove("./test.db")
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

# Poblar la base de datos de test con datos de ejemplo
with TestingSessionLocal() as db:
    game = Game(game_id=1, name="Test Game", status="esperando jugadores", max_players=6, min_players=2, players_amount=1)
    player = Player(player_id=1, name="Test Player", host=True, birth_date=datetime.date(2000, 1, 1), turn_order=1, game_id=1)
    card = Card(card_id=1, type="Test", picked_up=False, dropped=False, player_id=None, game_id=1)
    db.add(game)
    db.add(player)
    db.add(card)
    db.commit()

def test_list_cards_ingame():
    # Suponiendo que existe un game_id válido en la base de datos
    game_id = 1
    response = client.get(f"/lobby/cards/{game_id}")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert isinstance(response.json(), list)
    else:
        assert response.json()["detail"] == "No cards found for the given game_id"

def test_pickup_a_card():
    # Suponiendo que existen player_id y game_id válidos
    player_id = 1
    game_id = 1
    response = client.put(f"/cards/pick_up/{player_id},{game_id}")
    assert response.status_code == 200
    # Puede devolver None o un mensaje de juego terminado
    assert response.json() is None or "message: Game finished" in str(response.json())

def test_list_card_ofplayer_has_card():
    # Suponiendo que existe un player_id válido en la base de datos
    player_id = 1
    response = client.get(f"/lobby/list/cards/{player_id}")
    cards = response.json()  # Esto es una lista de dicts
    assert any(card["card_id"] == 1 for card in cards)
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert isinstance(response.json(), list)
    else:
        assert response.json()["detail"] == "No cards found for the given player_id"

def test_discard_card():
    # Suponiendo que existe un player_id válido
    player_id = 1
    response = client.put(f"/cards/drop/{player_id}")
    assert response.status_code == 200
    # Puede devolver mensaje de éxito o que todas las cartas fueron descartadas
    assert "message:" in str(response.json())

def test_list_card_ofplayer():
    # Suponiendo que existe un player_id válido en la base de datos
    player_id = 1
    response = client.get(f"/lobby/list/cards/{player_id}")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert isinstance(response.json(), list)
    else:
        assert response.json()["detail"] == "No cards found for the given player_id"

def test_pickup_card_twice():
    player_id = 1
    game_id = 1
    # Primer pick up debe funcionar
    response1 = client.put(f"/cards/pick_up/{player_id},{game_id}")
    assert response1.status_code == 200
    # Segundo pick up debe devolver mensaje de juego terminado o no asignar carta
    response2 = client.put(f"/cards/pick_up/{player_id},{game_id}")
    assert response2.status_code == 200
    assert response2.json() is None or "message: Game finished" in str(response2.json())

def test_discard_card_twice():
    player_id = 1
    # Primer discard debe funcionar
    response1 = client.put(f"/cards/drop/{player_id}")
    assert response1.status_code == 200
    assert "message:" in str(response1.json())
    # Segundo discard debe devolver mensaje de que todas las cartas fueron descartadas
    response2 = client.put(f"/cards/drop/{player_id}")
    assert response2.status_code == 200
    assert "All cards dropped" in str(response2.json()) or "message:" in str(response2.json())

