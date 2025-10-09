from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Card , Game
from src.database.services.services_cards import only_6
from src.schemas.card_schemas import Card_Response
import random

card = APIRouter()

@card.get("/lobby/cards/{game_id}", tags=["Cards"], response_model=list[Card_Response])
def list_cards_ingame(game_id: int, db: Session = Depends(get_db)):
    cards = db.query(Card).filter(Card.game_id == game_id).all()
    if not cards:
        raise HTTPException(status_code=404, detail="No cards found for the given game_id")
    return cards

@card.get("/lobby/list/cards/{player_id}", tags=["Cards"], response_model=list[Card_Response])
def list_card_ofplayer(player_id: int, db: Session = Depends(get_db)):
    cards = db.query(Card).filter(Card.player_id == player_id, Card.dropped == False).all()
    if not cards:
        raise HTTPException(status_code=404, detail="No cards found for the given player_id")
    return cards

@card.put("/cards/pick_up/{player_id},{game_id}", status_code=200, tags=["Cards"], response_model=Card_Response)
def pickup_a_card(player_id: int, game_id: int, db: Session = Depends(get_db)):
    has_6_cards = only_6(player_id, db)
    if has_6_cards:
        raise HTTPException(status_code=400, detail="The player already has 6 cards")
    deck = db.query(Card).filter(Card.game_id == game_id, Card.player_id == None).all()
    game = db.query(Game).filter(Game.game_id == game_id).first()
    random.shuffle(deck)
    if not deck:
        raise HTTPException(status_code=404, detail="Game finished")
    if game.cards_left is None:
        raise HTTPException(status_code=404, detail="Game finished")
    card = deck[0]
    try:
        card.picked_up = True
        card.player_id = player_id
        game.cards_left = game.cards_left - 1
        db.commit()
        db.refresh(card)
        db.refresh(game)
        return card
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error assigning card to player: {str(e)}")


@card.put("/cards/drop/{player_id}" , status_code=200, tags = ["Cards"], response_model=Card_Response)
def discard_card(player_id : int , db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.player_id == player_id , Card.dropped == False).first()
    if not card:
        raise HTTPException(status_code=404, detail="All cards dropped")       
    try:
        card.dropped = True
        card.picked_up = False
        db.commit()
        db.refresh(card)
        return card
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error assigning card to player: {str(e)}")
    
@card.put("/cards/game/drop/{player_id},{card_id}", status_code= 200 , tags = ["Cards"], response_model= Card_Response)
def select_card_to_discard(player_id : int, card_id : int, db: Session = Depends (get_db)) : 
    card = db.query(Card).filter(Card.player_id == player_id , Card.dropped == False, Card.card_id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="All cards dropped from player or card id invalid to player")       
    try:
        card.dropped = True
        card.picked_up = False
        db.commit()
        db.refresh(card)
        return card
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error assigning card to player: {str(e)}")
    
@card.get("/cards/draft/{game_id}", tags=["Cards"], response_model=list[Card_Response])
def get_draft_pile(game_id: int, db: Session = Depends(get_db)):
    """
    Obtiene las cartas que están actualmente visibles en el draft pile de la mesa.
    """
    draft_cards = db.query(Card).filter(
        Card.game_id == game_id,
        Card.draft == True
    ).all()

    if not draft_cards:
        raise HTTPException(status_code=404, detail="No cards found in the draft pile for this game.")
    
    return draft_cards