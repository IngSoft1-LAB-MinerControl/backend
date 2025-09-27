from fastapi import Depends
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Game 
from src.schemas.games_schemas import Game_Base



def update_players_on_game (game_id : int, db : Session = Depends(get_db)):
    game = db.query(Game).where(Game.game_id == game_id).first()
    if game.players_amount < game.max_players : 
        game.players_amount += 1
        if game.players_amount >= game.min_players : 
            game.status = 'bootable'
        db.add(game)
        try: 
            db.commit()
            db.refresh(game)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error updating amount of players in game: {str(e)}")  
    
        return game.players_amount

    else :
        game.status = 'Full'
        db.add(game)
        try: 
            db.commit()
            db.refresh(game)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error updating amount of players in game, changing game status to full: {str(e)}")  
        return None 



