from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Secrets

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
