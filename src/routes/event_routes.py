from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func  
from src.database.database import SessionLocal, get_db
from src.database.models import Card , Game , Detective , Event, Secrets, Set, Player
from src.database.services.services_cards import only_6 , replenish_draft_pile
from src.database.services.services_games import finish_game
from src.schemas.card_schemas import Card_Response
from src.database.services.services_websockets import broadcast_last_discarted_cards, broadcast_game_information , broadcast_player_state, broadcast_card_draft
from src.database.services.services_events import cards_off_table, look_into_ashes, one_more, early_train_paddington, another_victim
import random

events = APIRouter()




@events.put("/event/look_into_ashes/{player_id},{card_id}", status_code=200, tags=["Events"], response_model=Card_Response)
async def activate_look_into_ashes_event(player_id: int, card_id: int, db: Session = Depends(get_db)):
    # Validar player_id
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found.")
    # Validar card_id
    card = db.query(Card).filter(Card.card_id == card_id, Card.dropped == True).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found.")
    
    taken_card = look_into_ashes(player_id=player_id, card_id=card_id, db=db)
    await broadcast_game_information(card.game_id)
    await broadcast_last_discarted_cards(player_id)
    return taken_card