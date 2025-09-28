from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Card 
import random

card = APIRouter()

@card.get("/lobby/cards/{game_id}")
def list_cards_ingame(game_id : int , db: Session = Depends(get_db)):
    cards = db.query(Card).filter(Card.game_id == game_id).all() # .all() me devuelve una lista, si no hay nada devuelve lista vacia
    if not cards:
        raise HTTPException(status_code=404, detail="No cards found for the given game_id")
    return cards

@card.get("/lobby/list/cards/{player_id}")
def list_card_ofplayer(player_id : int , db: Session = Depends(get_db)):
    cards = db.query(Card).filter(Card.player_id == player_id).all() # .all() me devuelve una lista, si no hay nada devuelve lista vacia
    if not cards:
        raise HTTPException(status_code=404, detail="No cards found for the given player_id")
    return cards

@card.post("/cards/{game_id}")
def init_cards(game_id : int , db: Session = Depends(get_db)):
    new_cards_list = []
    for _ in range(61): 
        new_card_instance = Card(
        type="Carta generica",
        picked_up=False,
        dropped=False,
        player_id=None,
        game_id=game_id
        )
        new_cards_list.append(new_card_instance)

    try:
        db.add_all(new_cards_list)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating cards: {str(e)}")
    
    return {"message": "61 cards created successfully"}

@card.put("/cards/{players_id},{game_id}")
def pickup_a_card(player_id : int , game_id : int , db: Session = Depends(get_db)):
    deck = db.query(Card).filter(Card.game_id == game_id, Card.player_id == None).all()
    random.shuffle(deck)
    if deck:
        card = deck[0]
    else:
        return {"message: Game finished"}
    try:
        card.player_id = player_id
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error assigning card to player: {str(e)}")
    return None