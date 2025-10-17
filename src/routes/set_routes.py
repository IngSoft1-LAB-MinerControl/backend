from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func  
from src.schemas.set_schemas import Set_Response
from src.database.database import SessionLocal, get_db
from src.database.models import Card , Game , Detective , Event , Set, Player
from src.database.services.services_cards import only_6
from src.schemas.card_schemas import Card_Response , Detective_Response , Event_Response
from src.database.services.services_websockets import broadcast_last_discarted_cards, broadcast_player_state
import random

set = APIRouter()

@set.post("/sets_of2/{card_id},{card_id_2}", status_code=201, tags = ["Sets"])
async def play_set_of2(card_id : int , card_id_2:int , db:Session=Depends(get_db)):
    card_1 = db.query(Detective).filter(Detective.card_id == card_id).first()
    card_2 = db.query(Detective).filter(Detective.card_id == card_id_2).first()
    game = db.query(Game).filter(Game.game_id == card_1.game_id).first()
    game_id = game.game_id

    if not card_1 or not card_2:
        raise HTTPException(status_code=400, detail=f"Invalid card_id")
  
    if (card_1.quantity_set > 2 or card_2.quantity_set > 2):
        raise HTTPException(status_code=400, detail=f"You need one more detective to play this set")
    
    if (card_1.name == "Harley Quin Wildcard" and card_2.name == "Harley Quin Wildcard"):
        raise HTTPException(status_code=400 , detail=f"You can't play this set")
    
    if (card_1.name == "Harley Quin Wildcard"):
        new_set = Set(name = card_2.name , 
                      player_id = card_2.player_id ,
                      game_id = card_2.game_id)
        db.add(new_set)
        try:
            db.commit()
            db.refresh(new_set)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error creating set: {str(e)}")
        
    elif(card_2.name == "Harley Quin Wildcard" or card_1.name == card_2.name):
        new_set = Set(name = card_1.name ,
                      player_id = card_1.player_id ,
                      game_id = card_1.game_id)
        db.add(new_set)
        try:
            db.commit()
            db.refresh(new_set)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error creating set: {str(e)}")
   
    elif((card_1.name == "Tommy Beresford" and card_2.name == "Tuppence Beresford" )or
         (card_1.name == "Tuppence Beresford" and card_2.name == "Tommy Beresford")):
        new_set = Set(name = "Beresford brothers" , 
                      player_id = card_1.player_id ,
                      game_id = card_1.game_id)
        db.add(new_set)
        try:
            db.commit()
            db.refresh(new_set)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error creating set: {str(e)}")
        
    else: 
        raise HTTPException(status_code=400, detail=f"This are not two compatible detectives")
    
    card_1.set_id = new_set.set_id
    card_2.set_id = new_set.set_id
    card_1.player_id = None
    card_2.player_id = None 
    db.commit()
    db.refresh(card_1)
    db.refresh(card_2)
    await broadcast_player_state(game_id)
    return new_set

@set.post("/sets_of3/{card_id},{card_id_2},{card_id_3}", status_code=201, tags = ["Sets"])
async def play_set_of3(card_id : int , card_id_2: int , card_id_3: int , db:Session=Depends(get_db)):
    card_1 = db.query(Detective).filter(Detective.card_id == card_id).first()
    card_2 = db.query(Detective).filter(Detective.card_id == card_id_2).first()
    card_3 = db.query(Detective).filter(Detective.card_id == card_id_3).first()

    if not card_1 or not card_2 or not card_3:
        raise HTTPException(status_code=400, detail=f"Invalid card_id")
    
    if (card_1.quantity_set == 2 or card_2.quantity_set == 2 or card_3.quantity_set == 2):
        raise HTTPException(status_code=400, detail=f"You need just 2 cards to play this set")
    
    if (card_1.name == "Harley Quin Wildcard" and card_2.name == card_3.name):
        new_set = Set(name = card_2.name , 
                      player_id = card_2.player_id ,
                      game_id = card_2.game_id)
        db.add(new_set)
        try:
            db.commit()
            db.refresh(new_set)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error creating set: {str(e)}")
        
    elif((card_2.name == "Harley Quin Wildcard" and card_1.name == card_3.name) or
         (card_3.name == "Harley Quin Wildcard" and card_1.name == card_2.name)):
        new_set = Set(name = card_1.name ,
                      player_id = card_1.player_id ,
                      game_id = card_1.game_id)
        db.add(new_set)
        try:
            db.commit()
            db.refresh(new_set)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error creating set: {str(e)}")
        
    elif(card_1.name == card_2.name == card_3.name):
        new_set = Set(name = card_1.name ,
                      player_id = card_1.player_id ,
                      game_id = card_1.game_id)
        db.add(new_set)
        try:
            db.commit()
            db.refresh(new_set)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error creating set: {str(e)}")
        
    else: 
        raise HTTPException(status_code=400, detail=f"This are not three compatible detectives")
    


    card_1.set_id = new_set.set_id
    card_2.set_id = new_set.set_id
    card_3.set_id = new_set.set_id
    card_1.player_id = None
    card_2.player_id = None
    card_3.player_id = None
    db.commit()
    db.refresh(card_1)
    db.refresh(card_2)
    db.refresh(card_3)
    await broadcast_player_state(card_1.game_id)
    return new_set

@set.get("/sets/list/{player_id}", status_code = 201, response_model= Set_Response, tags = {"Sets"})
def get_set_player (player_id : int , db : Session = Depends(get_db)): 
    set = db.query(Set).filter(Set.player_id == player_id).first()
    if not set: 
        raise HTTPException(status_code=400, detail=f"Player does not have that set")

    return set 

@set.put ("/sets/steal/{player_id_to}/{set_id}", status_code= 201,response_model= Set_Response, tags= ["Sets"])
async def steal_set( player_id_to : int, set_id : int, db : Session = Depends(get_db)) :
    set = db.query(Set).filter(Set.set_id == set_id).first()
    if not set : 
        raise HTTPException(status_code=400, detail=f"Player does not have that set")
    player_id_2 = db.query(Player).filter(Player.player_id == player_id_to).first()
    if not player_id_2 : 
        raise HTTPException (status_code = 400, detail = f"Player id 2 does not exist") 


    set.player_id = player_id_to
    try : 
        db.commit()
        db.refresh(set)
        await broadcast_player_state(set.game_id)

        return set
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error stealing set: {str(e)}")