from fastapi import Depends
from sqlalchemy import extract
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Game, Player 
from src.schemas.games_schemas import Game_Base
from datetime import date 

today = date.today()
acBday = date(today.year,9, 15)

def update_players_on_game (game_id : int, db : Session = Depends(get_db)):
    game = db.query(Game).where(Game.game_id == game_id).first()
    if game.players_amount < game.max_players : 
        game.players_amount += 1
        if game.players_amount >= game.min_players : 
            game.status = 'bootable'
        if game.players_amount == game.max_players :
            game.status = 'Full'
        db.add(game)
        try: 
            db.commit()
            db.refresh(game)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error updating amount of players in game: {str(e)}")  
    
        return game.players_amount

    else :  
        return None 

def assign_turn_to_players (game_id : int, db :Session = Depends (get_db)) : 
    today = date.today()
    acBday = date(today.year,9, 15)
    game = db.query(Game).where(Game.game_id == game_id).first()
    print (game) 
    players = db.query(Player).filter(Player.game_id == game_id).all()
    players_birthday = db.query (Player.player_id, extract('month', Player.birth_date).label("month"), 
                        extract('day', Player.birth_date).label("day")).where(Player.game_id == game_id).all()
     
    turn_order = []
    for player_id, month, day in players_birthday :
        player_birthday_calc = date(today.year, int(month), int(day))
        diff_days = abs((acBday-player_birthday_calc).days)
        pos = 0 
        for i in turn_order : 
            if diff_days < i[1] :  
                break
            else : 
                pos += 1    

        turn_order.insert(pos,(player_id, diff_days))
    
    for player in players:
        index = 1 
        for i in turn_order : 
            if player.player_id == i[0] :
                break
            else : 
                index += 1
        player.turn_order = index
        db.add(player)
        try: 
            db.commit()
            db.refresh(player)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error setting turn of players in game: {str(e)}") 
    
    game.current_turn = 1
    db.add(game)
    try:
        db.commit()
        db.refresh(game)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error setting current turn in game: {str(e)}") 
    return game





