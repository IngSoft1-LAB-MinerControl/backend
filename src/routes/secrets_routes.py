from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Player, Secrets
from src.database.services.services_websockets import broadcast_player_state , broadcast_game_information
from src.schemas.secret_schemas import Secret_Response
from src.database.services.services_secrets import reveal_secret as reveal_secret_service, hide_secret as hide_secret_service, steal_secret as steal_secret_service


secret = APIRouter()

@secret.get("/lobby/secrets/{player_id}", tags = ["Secrets"] , response_model= list[Secret_Response])
def list_secrets_of_player(player_id : int , db: Session = Depends(get_db)):
    player = db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found") 
    secrets = db.query(Secrets).filter(Secrets.player_id == player_id).all()
    if not secrets:
        raise HTTPException(status_code=404, detail="No secrets found for the given player_id")
    
    return secrets

@secret.get("/lobby/secrets_game/{game_id}", tags = ["Secrets"] , response_model= list[Secret_Response])
def list_secrets_of_game(game_id : int , db: Session = Depends(get_db)):
    secrets = db.query(Secrets).filter(Secrets.game_id == game_id).all()
    if not secrets:
        raise HTTPException(status_code=404, detail="No secrets found for the given game_id")
    
    return secrets

# 3 routes para revelar secreto 
@secret.put("/secrets/reveal/{secret_id}", tags = ["Secrets"] , response_model= Secret_Response)
async def reveal_secret(secret_id : int ,  db: Session = Depends(get_db)):
    # 2. Llamar a la función de servicio con los parámetros recibidos
    # La función de servicio se encarga de toda la lógica y las excepciones.
    revealed = await reveal_secret_service(secret_id=secret_id, db=db)
    await broadcast_game_information(revealed.game_id)
    return revealed

# 1 route para ocultar secreto 
@secret.put("/secrets/hide/{secret_id}", tags = ["Secrets"] , response_model= Secret_Response)
async def hide_secret(secret_id : int , db: Session = Depends(get_db)):
    # 2. Llamar a la función de servicio con los parámetros recibidos
    # La función de servicio se encarga de toda la lógica y las excepciones.
    hidden = hide_secret_service(secret_id=secret_id, db=db)
    await broadcast_game_information(hidden.game_id)
    return hidden

# 1 route para robar secreto
@secret.put("/secrets/steal/{secret_id},{target_player_id}", tags = ["Secrets"] , response_model= Secret_Response)
async def steal_secret(secret_id : int , target_player_id: int, db: Session = Depends(get_db)):
    # 2. Llamar a la función de servicio con los parámetros recibidos
    # La función de servicio se encarga de toda la lógica y las excepciones.
    # se elije primero el jugador al que le robo y depues el jugador al que se lo doy
    stolen = steal_secret_service(target_player_id=target_player_id, secret_id=secret_id, db=db)
    await broadcast_game_information(stolen.game_id)
    return stolen
