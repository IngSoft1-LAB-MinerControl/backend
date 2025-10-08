from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from src.database.models import Game 
from src.schemas.games_schemas import Game_Response
from src.webSocket.connection_manager import manager
import json 


async def broadcast_available_games(db: Session):
    """
    Obtiene las partidas disponibles y las envía a todos los clientes conectados.
    """
    games = db.query(Game).filter(
        (Game.status == "bootable") | (Game.status == "waiting players")
    ).all()
    
    # 2. Conviertes cada objeto ORM a un objeto Pydantic Game_Response
    # Pydantic leerá los atributos (game.name, game.status, etc.) automáticamente
    gamesResponse = [Game_Response.model_validate(game) for game in games]
    
    # 3. Usas jsonable_encoder para convertir los objetos Pydantic a una
    # estructura de datos de Python compatible con JSON (listas de diccionarios)
    gamesResponseJson = jsonable_encoder(gamesResponse)

    
    # manager.broadcast espera un string, así que convertimos la lista a un JSON string.
    
    await manager.broadcast(json.dumps(gamesResponseJson))
