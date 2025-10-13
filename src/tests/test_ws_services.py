import datetime
from fastapi import HTTPException
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from src.database.models import Game, Player, Card, Secrets # Importa tus modelos
from src.database.services.services_websockets import broadcast_available_games, broadcast_game_information, broadcast_last_discarted_cards, broadcast_lobby_information

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_db_session():
    """Crea un mock de la sesión de SQLAlchemy."""
    return MagicMock()

# Usamos 'patch' para reemplazar los managers globales con mocks durante la prueba
@patch('src.database.services.services_websockets.lobbyManager', new_callable=AsyncMock)
async def test_broadcast_available_games(mock_lobby_manager, mock_db_session):
    # 1. Preparación (Arrange)
    
    # Simular los datos que devolvería la base de datos
    mock_game_1 = Game(game_id=1, name="Partida 1", status="waiting players", max_players = 6, min_players = 3, players_amount = 2)
    mock_game_2 = Game(game_id=2, name="Partida 2", status="bootable", max_players = 6, min_players = 2, players_amount = 2)
    
    # Configurar el mock de la DB para que devuelva los datos simulados
    mock_db_session.query.return_value.all.return_value = [mock_game_1, mock_game_2]
    
    # 2. Actuación (Act)
    await broadcast_available_games(mock_db_session)

    # 3. Aserción (Assert)

    # Verificar que se llamó al broadcast del manager
    mock_lobby_manager.broadcast.assert_awaited_once()

    # Verificar que los datos enviados son correctos
    # Obtenemos los argumentos con los que fue llamado el mock
    call_args, _ = mock_lobby_manager.broadcast.call_args
    sent_json_str = call_args[0]
    
    # Convertimos el string JSON enviado a un objeto Python para compararlo
    sent_data = json.loads(sent_json_str)

    assert len(sent_data) == 2
    assert sent_data[0]['name'] == "Partida 1"
    assert sent_data[1]['status'] == "bootable"

@patch('src.database.services.services_websockets.gameManager', new_callable=AsyncMock)
async def test_broadcast_lobby_information_success(mock_game_manager, mock_db_session):
    # 1. Arrange: Preparamos los datos simulados que devolverá la DB
    game_id = 1
    mock_game = Game(
        game_id=game_id, name="Lobby de Prueba", status="waiting players",
        max_players=6, min_players=4, players_amount=2
    )
    mock_players = [
        Player(player_id=1, name="Jugador 1", game_id=1, host=True, birth_date = datetime.date(2000, 1, 1)),
        Player(player_id=2, name="Jugador 2", game_id=1, host=False, birth_date= datetime.date(2000, 4, 4))
    ]
    # Configuramos el mock de la DB para que devuelva nuestros datos
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_game
    mock_db_session.query.return_value.filter.return_value.all.return_value = mock_players
    
    # 2. Act: Llamamos a la función
    await broadcast_lobby_information(mock_db_session, game_id)

    # 3. Assert: Verificamos que se hicieron dos broadcasts
    assert mock_game_manager.broadcast.await_count == 2
    
    # Verificamos la primera llamada (información del juego)
    first_call_args = mock_game_manager.broadcast.await_args_list[0].args
    first_call_data = json.loads(first_call_args[0])
    assert first_call_data['type'] == 'game'
    assert json.loads(first_call_data['data'])['name'] == "Lobby de Prueba"
    assert first_call_args[1] == game_id # Verifica el game_id

    # Verificamos la segunda llamada (información de los jugadores)
    second_call_args = mock_game_manager.broadcast.await_args_list[1].args
    second_call_data = json.loads(second_call_args[0])
    assert second_call_data['type'] == 'players'
    assert len(second_call_data['data']) == 2
    assert second_call_data['data'][0]['name'] == "Jugador 1"
    assert second_call_args[1] == game_id # Verifica el game_id

@patch('src.database.services.services_websockets.gameManager', new_callable=AsyncMock)
async def test_broadcast_lobby_information_game_not_found(mock_game_manager, mock_db_session):
    # 1. Arrange: Configuramos la DB para que no encuentre el juego
    mock_db_session.query.return_value.filter.return_value.first.return_value = None
    
    # 2. Act
    await broadcast_lobby_information(mock_db_session, game_id=999)

    # 3. Assert: Verificamos que NO se llamó al broadcast
    mock_game_manager.broadcast.assert_not_awaited()



@patch('src.database.services.services_websockets.gameManager', new_callable=AsyncMock)
@patch('src.database.services.services_websockets.SessionLocal')
async def test_broadcast_game_information_success(mock_session_local, mock_game_manager, mock_db_session):
    # 1. Arrange: Configuramos el mock de SessionLocal para que devuelva nuestra sesión mockeada
    mock_session_local.return_value = mock_db_session
    game_id = 1
    mock_game = Game(
        game_id=game_id, name="Partida en Juego", status="in progress",
        max_players=6, min_players=4, players_amount=4
    )
    # Los jugadores ahora necesitan más campos para Player_State
    mock_players = [
        Player(player_id=1, name="Jugador 1",game_id = 1,host = True, turn_order=2,birth_date = datetime.date(2000, 1, 1), cards=[], secrets=[]),
        Player(player_id=2, name="Jugador 2",game_id = 1 ,host = False,turn_order=1,birth_date = datetime.date(2000, 4, 4) , cards=[], secrets=[])
    ]
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_game
    mock_db_session.query.return_value.options.return_value.filter.return_value.all.return_value = mock_players
    
    # 2. Act
    await broadcast_game_information(game_id)

    # 3. Assert
    assert mock_game_manager.broadcast.await_count == 2
    
    # Verificamos la llamada para "gameUpdated"
    game_updated_call_args = mock_game_manager.broadcast.await_args_list[0].args
    game_updated_data = json.loads(game_updated_call_args[0])
    assert game_updated_data['type'] == 'gameUpdated'
    assert json.loads(game_updated_data['data'])['status'] == 'in progress'

    # Verificamos la llamada para "playersState"
    players_state_call_args = mock_game_manager.broadcast.await_args_list[1].args
    players_state_data = json.loads(players_state_call_args[0])
    assert players_state_data['type'] == 'playersState'
    assert len(players_state_data['data']) == 2
    

# --- Pruebas para broadcast_last_discarted_cards ---

@patch('src.database.services.services_websockets.gameManager', new_callable=AsyncMock)
@patch('src.database.services.services_websockets.SessionLocal')
async def test_broadcast_last_discarted_cards_success(mock_session_local, mock_game_manager, mock_db_session):
    # 1. Arrange
    mock_session_local.return_value = mock_db_session
    player_id = 1
    game_id = 10
    mock_player = Player(player_id=player_id, name="Jugador 1",game_id = game_id,host = True, turn_order=2,birth_date = datetime.date(2000, 1, 1), cards=[], secrets=[])
    mock_cards = [
        Card(card_id=101, type="Accion", game_id=game_id,player_id= player_id, dropped=True,picked_up = True,draft = False ,discardInt=5),
        Card(card_id=102, type="Accion", game_id=game_id,player_id = player_id, dropped=True,picked_up = True ,draft = False,discardInt=4)
    ]
    # Configurar la cadena de llamadas para encontrar al jugador
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_player
    # Configurar la cadena de llamadas para encontrar las cartas
    (mock_db_session.query.return_value.filter.return_value
     .order_by.return_value.limit.return_value.all.return_value) = mock_cards

    # 2. Act
    await broadcast_last_discarted_cards(player_id)

    # 3. Assert
    mock_game_manager.broadcast.assert_awaited_once()
    call_args, _ = mock_game_manager.broadcast.await_args
    sent_data = json.loads(call_args[0])
    assert call_args[1] == game_id
    assert sent_data['type'] == 'droppedCards'
    assert len(sent_data['data']) == 2
    

@patch('src.database.services.services_websockets.gameManager', new_callable=AsyncMock)
@patch('src.database.services.services_websockets.SessionLocal')
async def test_broadcast_last_discarted_cards_no_cards_found(mock_session_local, mock_game_manager, mock_db_session):
    # 1. Arrange
    mock_session_local.return_value = mock_db_session
    player_id = 1
    game_id = 10
    mock_player = Player(player_id=player_id, name="Jugador 1",game_id = game_id,host = True, turn_order=2,birth_date = datetime.date(2000, 1, 1), cards=[], secrets=[])
    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_player
    # Configuramos para que la búsqueda de cartas devuelva una lista vacía
    (mock_db_session.query.return_value.filter.return_value
     .order_by.return_value.limit.return_value.all.return_value) = []

    # 2. Act & 3. Assert
    # Verificamos que la función lanza la excepción esperada
    with pytest.raises(HTTPException) as exc_info:
        await broadcast_last_discarted_cards(player_id)
    
    # Opcional: verificar detalles de la excepción
    assert exc_info.value.status_code == 404
    
    # Muy importante: verificar que no se intentó hacer un broadcast
    mock_game_manager.broadcast.assert_not_awaited()
