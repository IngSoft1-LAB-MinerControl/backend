"""
Tests for the Set creation and manipulation endpoints.

This file uses a dedicated fixture `setup_data` to create a common,
clean state (game, players, cards) for each test, ensuring isolation and
reproducibility. The `client` fixture from conftest.py is used for API calls.
"""
import datetime
import pytest

# Nota: Todas las importaciones de configuración de DB y TestClient se han ido.
# Solo importamos los modelos que necesitamos para la fixture de setup.
from src.database.models import Game, Player, Detective, Set
from unittest.mock import AsyncMock

# Mantén tu fixture setup_data original, la que no tiene transacciones separadas
@pytest.fixture
def setup_data(db_session):
    # Crear entidades de base
    game = Game(game_id=1, name="Test Game", status="in course", max_players=6, min_players=2, players_amount=2)
    player1 = Player(name="Player1", host=True, birth_date=datetime.date(2000, 1, 1), turn_order=1, game_id=1)
    player2 = Player(name="Player2", host=False, birth_date=datetime.date(2000, 1, 2), turn_order=2, game_id=1)
    db_session.add_all([game, player1, player2])
    
    # Crear cartas de detective
    detectives = [
        Detective(card_id=1, type="detective", name="Parker Pyne", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=2),
        Detective(card_id=2, type="detective", name="Parker Pyne", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=2),
        Detective(card_id=3, type="detective", name="Harley Quin Wildcard", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=2),
        Detective(card_id=4, type="detective", name="Miss Marple", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=3),
        Detective(card_id=5, type="detective", name="Miss Marple", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=3),
        Detective(card_id=6, type="detective", name="Miss Marple", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=3),
        Detective(card_id=7, type="detective", name="Tommy Beresford", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=2),
        Detective(card_id=8, type="detective", name="Tuppence Beresford", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=2),
        Detective(card_id=9, type="detective", name="Hercule Poirot", picked_up=True, dropped=False, player_id=1, game_id=1, quantity_set=3),
    ]
    db_session.add_all(detectives)
    db_session.commit()
    return db_session # Devolvemos la sesión por si la necesitamos


# --- Tests para Sets de 2 Cartas ---

# 2. AÑADE `mocker` A LA FIRMA DEL TEST
def test_set_of2_same_name(client, setup_data, mocker):
    
    # 3. USA `mocker.patch` PARA REEMPLAZAR LA FUNCIÓN PROBLEMÁTICA
    # Le decimos que reemplace `broadcast_player_state` DENTRO del módulo `set_routes`
    # con un mock asíncrono que no hará nada.
    mock_broadcast = mocker.patch(
        'src.routes.set_routes.broadcast_player_state', 
        new_callable=AsyncMock
    )

    # Ahora, cuando llamemos al endpoint, la llamada a broadcast_player_state será interceptada
    response = client.post("/sets_of2/1,2")

    # El test ya no fallará por el ValidationError
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Parker Pyne"

    # 4. (Opcional pero recomendado) VERIFICA QUE EL BROADCAST FUE LLAMADO
    # Esto asegura que tu endpoint sigue intentando llamar a la función,
    # solo que nosotros la interceptamos.
    mock_broadcast.assert_awaited_once_with(1) # Verificamos que se llamó con game_id=1

def test_set_of2_with_wildcard(client, setup_data, mocker):
    mock_broadcast = mocker.patch(
        'src.routes.set_routes.broadcast_player_state', 
        new_callable=AsyncMock
    )
    
    response = client.post("/sets_of2/1,3")
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Parker Pyne"
    
    response2 = client.post("/sets_of2/3,2")
    assert response2.status_code == 201
    data2 = response2.json()
    assert data2["name"] == "Parker Pyne"

    mock_broadcast.call_count == 2

def test_set_of2_beresford_brothers(client, setup_data,mocker):
    mock_broadcast = mocker.patch(
        'src.routes.set_routes.broadcast_player_state', 
        new_callable=AsyncMock
    )
    
    response = client.post("/sets_of2/7,8")
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Beresford brothers"
    mock_broadcast.assert_awaited_once_with(1)

def test_set_of2_invalid_card_id(client, setup_data):
    # No existe card_id 99
    response = client.post("/sets_of2/1,99")
    assert response.status_code == 400
    assert "Invalid card_id" in response.json()["detail"]

def test_set_of2_wrong_quantity(client, setup_data):
    # Usar una carta de set de 3 en un endpoint de set de 2
    response = client.post("/sets_of2/4,5")
    assert response.status_code == 400
    assert "You need one more detective" in response.json()["detail"]

def test_set_of2_not_compatible(client, setup_data):
    # Dos detectives distintos sin wildcard ni relación de hermanos
    response = client.post("/sets_of2/1,7")
    assert response.status_code == 400
    assert "not two compatible detectives" in response.json()["detail"]

# --- Tests para Sets de 3 Cartas ---

def test_set_of3_same_name(client, setup_data, mocker):
    mock_broadcast = mocker.patch(
        'src.routes.set_routes.broadcast_player_state', 
        new_callable=AsyncMock
    )
    response = client.post("/sets_of3/4,5,6")
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Miss Marple"

    mock_broadcast.assert_awaited_once_with(1)

def test_set_of3_with_wildcard(client, setup_data,mocker):
    mock_broadcast = mocker.patch(
        'src.routes.set_routes.broadcast_player_state', 
        new_callable=AsyncMock
    )
    response = client.post("/sets_of3/3,4,5")
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Miss Marple"
    mock_broadcast.assert_awaited_once_with(1)

def test_set_of3_invalid_card_id(client, setup_data):
    response = client.post("/sets_of3/4,5,99")
    assert response.status_code == 400
    assert "Invalid card_id" in response.json()["detail"]

def test_set_of3_not_compatible(client, setup_data):
    response = client.post("/sets_of3/1,4,7")
    assert response.status_code == 400
    assert "You need just 2 cards to play this set" in response.json()["detail"]

# --- Tests para Endpoints Adicionales ---

def test_get_set_player(client, setup_data,mocker):
    mock_broadcast = mocker.patch(
        'src.routes.set_routes.broadcast_player_state', 
        new_callable=AsyncMock
    )
    # Arrange: Primero crear un set

    create_response = client.post("/sets_of2/1,2")
    assert create_response.status_code == 201
    set_id = create_response.json()["set_id"]
    
    # Act
    response = client.get(f"/sets/list/{set_id}")
    
    # Assert
    assert response.status_code == 201 
    data = response.json()
    # Asumiendo que el endpoint devuelve un objeto Set con el ID del jugador
    assert data["player_id"] == 1
    mock_broadcast.assert_awaited_once_with(1)

def test_steal_set(client, setup_data, mocker):
    # Arrange: Crear un set para el jugador 1
    mock_broadcast = mocker.patch(
        'src.routes.set_routes.broadcast_player_state', 
        new_callable=AsyncMock
    )
    create_response = client.post("/sets_of2/1,2")
    assert create_response.status_code == 201
    set_id = create_response.json()["set_id"]

    # Act: El jugador 2 roba el set 
    # (Asumo que la URL es /sets/steal/{target_player_id}/{thief_player_id}/{set_id})
    response = client.put(f"/sets/steal/2/{set_id}")
    if response.status_code != 201:
        print("DEBUG - Mensaje de error de la API:", response.json())
    
    # Assert
    assert response.status_code == 201 # PUT exitoso debería ser 200
    data = response.json()
    assert data["player_id"] == 2
    mock_broadcast.call_count == 2
    