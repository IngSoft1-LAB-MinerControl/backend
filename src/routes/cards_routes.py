from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Card 
from src.database.services.services_cards import only_6
import random

card = APIRouter()

@card.get("/lobby/cards/{game_id}",tags = ["Cards"])
def list_cards_ingame(game_id : int , db: Session = Depends(get_db)):
    cards = db.query(Card).filter(Card.game_id == game_id).all() # .all() me devuelve una lista, si no hay nada devuelve lista vacia
    if not cards:
        raise HTTPException(status_code=404, detail="No cards found for the given game_id")
    return cards

@card.get("/lobby/list/cards/{player_id}", tags = ["Cards"])
def list_card_ofplayer(player_id : int , db: Session = Depends(get_db)):
    cards = db.query(Card).filter(Card.player_id == player_id , Card.dropped == False).all() # .all() me devuelve una lista, si no hay nada devuelve lista vacia
    if not cards:
        raise HTTPException(status_code=404, detail="No cards found for the given player_id")
    return cards

@card.put("/cards/pick_up/{player_id},{game_id}" , status_code=200, tags = ["Cards"])
def pickup_a_card(player_id : int , game_id : int , db: Session = Depends(get_db)):
    has_6_cards = only_6(player_id , db)
    if has_6_cards: 
        raise HTTPException(status_code=400, detail="The player already has 6 cards")
    deck = db.query(Card).filter(Card.game_id == game_id, Card.player_id == None).all()
    random.shuffle(deck)
    if deck:
        card = deck[0]
    else:
        return {"message: Game finished"}
    try:
        card.picked_up = True
        card.player_id = player_id
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error assigning card to player: {str(e)}")
    return None
@card.put("/cards/drop/{player_id}" , status_code=200, tags = ["Cards"])
def discard_card(player_id : int , db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.player_id == player_id , Card.dropped == False).first()
    if not card:
        return {"message: All cards dropped"}       
    try:
        card.dropped = True
        card.picked_up = False
        db.commit()
        return {"message: card dropped" , card.card_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error assigning card to player: {str(e)}")