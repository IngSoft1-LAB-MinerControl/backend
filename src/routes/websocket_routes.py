import json
from fastapi import Depends, HTTPException, WebSocket, APIRouter
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session 
from src.schemas.games_schemas import Game_Response
from src.schemas.players_schemas import Player_Base
from src.database.models import Game, Player
from src.database.database import get_db
from src.database.services.services_websockets import broadcast_available_games, broadcast_lobby_information
from src.webSocket.connection_manager import lobbyManager , gameManager

ws = APIRouter()

@ws.websocket("/ws/games/availables", name="ws_available_games")
async def ws_available_games(websocket: WebSocket, db: Session = Depends(get_db)):
    await lobbyManager.connect(websocket)
    # Envía la lista actual de partidas tan pronto como el cliente se conecta
    await broadcast_available_games(db)
    try:
        while True:
            # Mantenemos la conexión abierta. 
            # El receive_text es solo para detectar cuando el cliente se desconecta.
            await websocket.receive_text()
    except Exception:
        # Cuando el cliente se desconecta, se lanza una excepción
        pass 
        # Opcional: podrías notificar a los demás si fuera necesario, 
        # pero para una lista de partidas no hace falta.
    finally : 
        lobbyManager.disconnect(websocket)

@ws.websocket("/ws/lobby/{game_id}", name = "Players from lobby")
async def ws_list_players(websocket : WebSocket,game_id : int ,db:Session = Depends(get_db)) : 
    game = db.query(Game).filter(Game.game_id == game_id).first() # .all() me devuelve una lista, si no hay nada devuelve lista vacia
    if not game:
        await websocket.close(code=4004, reason="Game not found")
        return 
    await gameManager.connect(websocket, game_id)
    
    try : 
        await broadcast_lobby_information(db, game_id)
        
        while True:
            # Mantenemos la conexión abierta para detectar cuando el cliente se va.
            await websocket.receive_text()

    except Exception:
        # Esta parte se ejecuta si el cliente cierra la pestaña o pierde la conexión.
        pass
    finally:
        # Nos aseguramos de desconectar al cliente del canal de la partida.
        gameManager.disconnect(websocket, game_id)
      
