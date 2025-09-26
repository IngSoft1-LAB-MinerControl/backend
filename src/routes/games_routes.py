from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Lobby 
from src.schemas.lobbies_schemas import Lobby_Base

lobby = APIRouter()

@lobby.get("/lobbies")
def list_lobbies (db: Session = Depends(get_db)) :
    return db.query(Lobby).all()



@lobby.post ("/lobbies", status_code=201) #devolvia un int y queria devolver una response con el schema de game_base
def create_lobby (lobby : Lobby_Base, db: Session = Depends(get_db)) : 
    new_lobby = Lobby (status = lobby.status,
                        max_players = lobby.max_players,
                        min_players = lobby.min_players,
                        name = lobby.name)
    db.add(new_lobby)
    try:
        db.commit()
        db.refresh(new_lobby)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating lobby: {str(e)}")
    return new_lobby.lobby_id


@lobby.delete("/lobby/{lobby_id}", status_code=204)
def delete_lobby(lobby_id: int, db:Session = Depends(get_db)):
    lobby = db.get(Lobby, lobby_id) 
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")
    try:
        db.delete(lobby)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting lobby: {str(e)}")
    return None

    




