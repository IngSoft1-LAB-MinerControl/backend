import os
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Game, Player, Secrets
from src.database.database import get_db
from fastapi.testclient import TestClient
from src.main import app
from unittest.mock import patch

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
    game = Game(game_id=1, name="Secret Game", status="en curso", max_players=4, min_players=2, players_amount=2)
    # Jugador 1 con un secreto
    player1 = Player(player_id=1, name="Secret Player", host=True, birth_date=datetime.date(2000, 1, 1), game_id=1)
    secret1 = Secrets(secret_id=1, murderer=True, acomplice=False, revelated=False, player_id=1, game_id=1)
    # Jugador 2 sin secretos
    player2 = Player(player_id=2, name="Innocent Player", host=False, birth_date=datetime.date(2001, 1, 1), game_id=1)
    # Jugador 3 para robar secretos
    player3 = Player(player_id=3, name="Target Player", host=False, birth_date=datetime.date(2002, 2, 2), game_id=1)
    # Secreto revelado
    secret2 = Secrets(secret_id=2, murderer=False, acomplice=False, revelated=True, player_id=1, game_id=1)
    # Secreto para robar
    secret3 = Secrets(secret_id=3, murderer=False, acomplice=False, revelated=False, player_id=1, game_id=1)
    
    db.add(game)
    db.add(player1)
    db.add(secret1)
    db.add(player2)
    db.add(player3)
    db.add(secret2)
    db.add(secret3)
    db.commit()

def test_list_secrets_of_player_success():
    response = client.get("/lobby/secrets/1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["murderer"] is True

def test_list_secrets_of_player_with_no_secrets():
    # El jugador 2 existe pero no tiene secretos asignados
    response = client.get("/lobby/secrets/2")
    assert response.status_code == 404
    assert response.json()["detail"] == "No secrets found for the given player_id"

def test_list_secrets_of_nonexistent_player():
    # El jugador 999 no existe
    response = client.get("/lobby/secrets/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Player not found"

def test_list_secrets_of_game_success():
    response = client.get("/lobby/secrets_game/1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["game_id"] == 1

def test_list_secrets_of_game_with_no_secrets():
    # El juego 999 no existe
    response = client.get("/lobby/secrets_game/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "No secrets found for the given game_id"

def test_reveal_secret_success():
    response = client.put("/secrets/reveal/1")
    assert response.status_code == 200
    data = response.json()
    assert data["revelated"] is True

def test_reveal_secret_not_found():
    response = client.put("/secrets/reveal/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Secret not found"

def test_reveal_secret_already_revealed():
    # Primero revelar el secreto
    client.put("/secrets/reveal/2")
    # Intentar revelar el mismo secreto de nuevo
    response = client.put("/secrets/reveal/2")
    assert response.status_code == 400
    assert response.json()["detail"] == "Secret is already revealed"

def test_hide_secret_success():
    # Primero revelar el secreto
    client.put("/secrets/reveal/1")
    # Ocultar el secreto
    response = client.put("/secrets/hide/1")
    assert response.status_code == 200
    data = response.json()
    assert data["revelated"] is False

def test_hide_secret_not_found():
    response = client.put("/secrets/hide/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Secret not found"

def test_hide_secret_not_revealed():
    # Intentar ocultar un secreto que no está revelado
    response = client.put("/secrets/hide/1")
    assert response.status_code == 400
    assert response.json()["detail"] == "Secret is not revealed"

def test_steal_secret_success():
    # Robar el secreto 2 (ya revelado) al jugador 1 y dárselo al jugador 3
    response = client.put("/secrets/steal/2,3") # secret_id, target_player_id
    assert response.status_code == 200
    data = response.json()
    assert data["player_id"] == 3

def test_steal_secret_not_found():
    # Intentar robar un secreto que no existe
    response = client.put("/secrets/steal/999,3") # secret_id, target_player_id
    assert response.status_code == 404
    assert response.json()["detail"] == "Secret not found"

def test_steal_secret_target_player_not_found():
    # Intentar robar un secreto a un jugador que no existe
    response = client.put("/secrets/steal/3,999") # secret_id, target_player_id
    assert response.status_code == 404
    assert response.json()["detail"] == "Player not found"

def test_deal_secrets_same_player_reintent():
    # Crear un juego y forzar que el asesino y el cómplice sean el mismo jugador
    with TestingSessionLocal() as db:
        game = Game(game_id=100, name="Same Player Game", status="waiting players", max_players=2, min_players=2, players_amount=2)
        player1 = Player(player_id=1001, name="Player 1", host=True, birth_date=datetime.date(2000, 1, 1), game_id=100)
        player2 = Player(player_id=1002, name="Player 2", host=False, birth_date=datetime.date(2001, 1, 1), game_id=100)
        # Crear suficientes secretos para repartir
        secret1 = Secrets(secret_id=1001, murderer=True, acomplice=False, revelated=False, player_id=None, game_id=100)
        secret2 = Secrets(secret_id=1002, murderer=False, acomplice=True, revelated=False, player_id=None, game_id=100)
        secret3 = Secrets(secret_id=1003, murderer=False, acomplice=False, revelated=False, player_id=None, game_id=100)
        secret4 = Secrets(secret_id=1004, murderer=False, acomplice=False, revelated=False, player_id=None, game_id=100)
        secret5 = Secrets(secret_id=1005, murderer=False, acomplice=False, revelated=False, player_id=None, game_id=100)
        secret6 = Secrets(secret_id=1006, murderer=False, acomplice=False, revelated=False, player_id=None, game_id=100)
        db.add_all([game, player1, player2, secret1, secret2, secret3, secret4, secret5, secret6])
        db.commit()

    # Intentar inicializar el juego (debería reintentar hasta que sean diferentes)
    response = client.post(f"/game/beginning/{100}")
    assert response.status_code == 202


def test_init_secrets_less_than_4_players():
    # Crear un juego con menos de 4 jugadores
    with TestingSessionLocal() as db:
        game = Game(game_id=102, name="Few Players Game", status="waiting players", max_players=3, min_players=2, players_amount=3)
        player1 = Player(player_id=1021, name="Player 1", host=True, birth_date=datetime.date(2000, 1, 1), game_id=102)
        player2 = Player(player_id=1022, name="Player 2", host=False, birth_date=datetime.date(2001, 1, 1), game_id=102)
        player3 = Player(player_id=1023, name="Player 3", host=False, birth_date=datetime.date(2002, 1, 1), game_id=102)
        db.add_all([game, player1, player2, player3])
        db.commit()

    # Inicializar los secretos (debería crear 3 * num_players - 1 secretos)
    response = client.post(f"/game/beginning/{102}")
    assert response.status_code == 202

def test_init_secrets_more_than_4_players():
    # Crear un juego con más de 4 jugadores
    with TestingSessionLocal() as db:
        game = Game(game_id=103, name="Many Players Game", status="waiting players", max_players=5, min_players=5, players_amount=5)
        player1 = Player(player_id=1031, name="Player 1", host=True, birth_date=datetime.date(2000, 1, 1), game_id=103)
        player2 = Player(player_id=1032, name="Player 2", host=False, birth_date=datetime.date(2001, 1, 1), game_id=103)
        player3 = Player(player_id=1033, name="Player 3", host=False, birth_date=datetime.date(2002, 1, 1), game_id=103)
        player4 = Player(player_id=1034, name="Player 4", host=False, birth_date=datetime.date(2003, 1, 1), game_id=103)
        player5 = Player(player_id=1035, name="Player 5", host=False, birth_date=datetime.date(2004, 1, 1), game_id=103)
        db.add_all([game, player1, player2, player3, player4, player5])
        db.commit()

    # Inicializar los secretos (debería crear 3 * num_players - 2 secretos)
    response = client.post(f"/game/beginning/{103}")
    assert response.status_code == 202