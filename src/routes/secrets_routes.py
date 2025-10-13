from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Player, Secrets
from src.schemas.secret_schemas import Secret_Response

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
