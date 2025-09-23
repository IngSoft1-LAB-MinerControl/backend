from fastapi import APIRouter, Depends  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Game 
from src.schemas.games_schemas import Game_Base

game = APIRouter()

@game.get("/games")
def list_games (db: Session = Depends(get_db)) :
    return db.query(Game).all()



@game.post ("/games")
def create_game (game : Game_Base, db: Session = Depends(get_db)) : 
    new_game = Game (status = game.status,
                        max_players = game.max_players,
                        min_players = game.min_players,
                        name = game.name)
    db.add(new_game)
    db.commit()
    db.refresh(new_game)
    return (new_game)


@game.delete("/game/{game_id}")
def delete_game(game_id: int, db:Session = Depends(get_db)):
    game = db.get(Game, game_id) 
    try:
        db.delete(game)
        db.commit()
    except Exception:
        db.rollback()
    return game 
    





