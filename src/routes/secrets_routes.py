from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Secrets

secret = APIRouter()

@secret.get("/lobby/secrets/{player_id}", tags = ["Secrets"])
def list_secrets_of_player(player_id : int , db: Session = Depends(get_db)):
    secrets = db.query(Secrets).filter(Secrets.player_id == player_id).all() # .all() me devuelve una lista, si no hay nada devuelve lista vacia
    if not secrets:
        raise HTTPException(status_code=404, detail="No secrets found for the given game_id")
    return secrets

