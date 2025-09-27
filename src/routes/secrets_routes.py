from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Secrets

secret = APIRouter()

@secret.post("/secrets/{game_id}")
def init_secrets(game_id : int , db: Session = Depends(get_db)):
    new_secret_list = []
    for _ in range(18): 
        new_secret = Secrets(murderer = False ,
                            acomplice = False ,
                            revelated = False ,
                            player_id = None,
                            game_id= game_id)
        new_secret_list.append(new_secret)

    try:
        db.add_all(new_secret_list)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating cards: {str(e)}")
    
    return {"message": "18 secrets created successfully"}


@secret.get("/lobby/secrets/{game_id}")
def list_secrets_ingame(game_id : int , db: Session = Depends(get_db)):
    cards = db.query(Secrets).filter(Secrets.game_id == game_id).all() # .all() me devuelve una lista, si no hay nada devuelve lista vacia
    if not cards:
        raise HTTPException(status_code=404, detail="No secrets found for the given game_id")
    return cards

