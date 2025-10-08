import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Game, Player, Card
from src.database.database import get_db
from fastapi.testclient import TestClient
from src.main import app

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

with TestingSessionLocal() as db:
    game = Game(game_id=1, name="Test Game", status="esperando jugadores", max_players=6, min_players=2, players_amount=1)
    player = Player(player_id=1, name="Test Player", host=True, birth_date=datetime.date(2000, 1, 1), turn_order=1, game_id=1)
    card = Card(card_id=1, type="Test", picked_up=False, dropped=False, player_id=None, game_id=1)
    db.add(game)
    db.add(player)
    db.add(card)
    db.commit()

def test_list_cards_ingame():
    game_id = 1
    response = client.get(f"/lobby/cards/{game_id}")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        cards = response.json()
        assert isinstance(cards, list)
        assert any("card_id" in card for card in cards)
    else:
        assert response.json()["detail"] == "No cards found for the given game_id"

def test_pickup_a_card():
    player_id = 1
    game_id = 1
    response = client.put(f"/cards/pick_up/{player_id},{game_id}")
    if response.status_code == 200:
        data = response.json()
        assert "card_id" in data
        assert data["player_id"] == player_id
        assert data["game_id"] == game_id
        assert data["picked_up"] is True
    else:
        assert response.status_code == 404
        assert response.json()["detail"] == "Game finished"
    with TestingSessionLocal() as db:
        card = db.query(Card).filter(Card.card_id == 1).first()
        assert card is not None
        assert card.player_id == 1
        assert card.game_id == 1
        assert card.picked_up is True

def test_list_card_ofplayer_has_card():
    player_id = 1
    response = client.get(f"/lobby/list/cards/{player_id}")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        cards = response.json()
        assert isinstance(cards, list)
        assert any(card["card_id"] == 1 for card in cards)
    else:
        assert response.json()["detail"] == "No cards found for the given player_id"

def test_discard_card():
    player_id = 1
    response = client.put(f"/cards/drop/{player_id}")
    if response.status_code == 200:
        data = response.json()
        assert "card_id" in data
        assert data["player_id"] == player_id
        assert data["dropped"] is True
        assert data["picked_up"] is False
    else:
        assert response.status_code == 404
        assert response.json()["detail"] == "All cards dropped"
    with TestingSessionLocal() as db:
        card = db.query(Card).filter(Card.card_id == 1).first()
        assert card is not None
        assert card.player_id == 1
        assert card.dropped is True
        assert card.picked_up is False

def test_list_card_ofplayer():
    player_id = 1
    response = client.get(f"/lobby/list/cards/{player_id}")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        cards = response.json()
        assert isinstance(cards, list)
    else:
        assert response.json()["detail"] == "No cards found for the given player_id"

def test_pickup_card_twice():
    player_id = 1
    game_id = 1
    response1 = client.put(f"/cards/pick_up/{player_id},{game_id}")
    assert response1.status_code == 200 or response1.status_code == 404
    response2 = client.put(f"/cards/pick_up/{player_id},{game_id}")
    # Debe devolver 404 si ya no hay cartas o el jugador ya tiene 6 cartas
    assert response2.status_code == 404 or response2.status_code == 400

def test_discard_card_twice():
    player_id = 1
    response1 = client.put(f"/cards/drop/{player_id}")
    assert response1.status_code == 200 or response1.status_code == 404
    response2 = client.put(f"/cards/drop/{player_id}")
    # Debe devolver 404 si ya no hay cartas para descartar
    assert response2.status_code == 404
    if response2.status_code == 404:
        assert response2.json()["detail"] == "All cards dropped"