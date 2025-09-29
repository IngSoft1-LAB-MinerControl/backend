import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Game, Player, Secrets
from src.database.database import get_db
from fastapi.testclient import TestClient
from src.main import app

# Configuración de la base de datos de prueba
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_secrets.db"
if os.path.exists("./test_secrets.db"):
    os.remove("./test_secrets.db")
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

# Poblar la base de datos con datos de ejemplo
with TestingSessionLocal() as db:
    game = Game(game_id=1, name="Secret Game", status="en curso", max_players=4, min_players=2, players_amount=1)
    player = Player(player_id=1, name="Secret Player", host=True, birth_date=datetime.date(2000, 1, 1), game_id=1)
    secret = Secrets(secret_id=1, murderer=True, acomplice=False, revelated=False, player_id=1, game_id=1)
    db.add(game)
    db.add(player)
    db.add(secret)
    db.commit()

def test_list_secrets_of_player_success():
    response = client.get("/lobby/secrets/1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["murderer"] == True

def test_list_secrets_of_player_not_found():
    response = client.get("/lobby/secrets/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "No secrets found for the given player_id"