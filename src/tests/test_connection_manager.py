import pytest
from unittest.mock import AsyncMock, call
from src.webSocket.connection_manager import ConnectionManagerLobby, ConnectionManagerGames

# Marcamos todas las pruebas en este archivo para que se ejecuten con pytest-asyncio
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_websocket():
    """Crea un mock de WebSocket con métodos asíncronos."""
    ws = AsyncMock()
    # accept() y send_text() son métodos que necesitamos simular
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws

# --- Pruebas para ConnectionManagerLobby ---

async def test_lobby_connect(mock_websocket):
    manager = ConnectionManagerLobby()
    await manager.connect(mock_websocket)
    
    # Verificar que el websocket fue aceptado
    mock_websocket.accept.assert_awaited_once()
    # Verificar que el websocket está en la lista de conexiones activas
    assert mock_websocket in manager.active_connections

def test_lobby_disconnect(mock_websocket):
    manager = ConnectionManagerLobby()
    manager.active_connections.append(mock_websocket) # Simular una conexión existente
    
    manager.disconnect(mock_websocket)
    
    assert mock_websocket not in manager.active_connections

async def test_lobby_broadcast(mock_websocket):
    manager = ConnectionManagerLobby()
    ws1 = mock_websocket
    ws2 = AsyncMock() # Un segundo websocket
    
    await manager.connect(ws1)
    await manager.connect(ws2)

    await manager.broadcast("Hola a todos")

    # Verificar que se intentó enviar el mensaje a ambos
    ws1.send_text.assert_awaited_once_with("Hola a todos")
    ws2.send_text.assert_awaited_once_with("Hola a todos")

# --- Pruebas para ConnectionManagerGames ---

async def test_games_connect(mock_websocket):
    manager = ConnectionManagerGames()
    game_id = 1
    
    await manager.connect(mock_websocket, game_id)
    
    mock_websocket.accept.assert_awaited_once()
    assert mock_websocket in manager.active_connections[game_id]
    assert len(manager.active_connections[game_id]) == 1

def test_games_disconnect(mock_websocket):
    manager = ConnectionManagerGames()
    game_id = 1
    # Simular una conexión existente
    manager.active_connections[game_id].append(mock_websocket)
    
    manager.disconnect(mock_websocket, game_id)
    
    # Verificar que el diccionario de esa partida se eliminó
    assert game_id not in manager.active_connections

async def test_games_broadcast(mock_websocket):
    manager = ConnectionManagerGames()
    game_id_1 = 1
    game_id_2 = 2
    
    ws1_game1 = mock_websocket
    ws2_game1 = AsyncMock()
    ws3_game2 = AsyncMock()
    
    # Conectar jugadores a diferentes partidas
    await manager.connect(ws1_game1, game_id_1)
    await manager.connect(ws2_game1, game_id_1)
    await manager.connect(ws3_game2, game_id_2)

    await manager.broadcast("Mensaje para partida 1", game_id_1)

    # Verificar que el mensaje solo se envió a los jugadores de la partida 1
    ws1_game1.send_text.assert_awaited_once_with("Mensaje para partida 1")
    ws2_game1.send_text.assert_awaited_once_with("Mensaje para partida 1")
    # Verificar que el jugador de la partida 2 NO recibió el mensaje
    ws3_game2.send_text.assert_not_awaited()