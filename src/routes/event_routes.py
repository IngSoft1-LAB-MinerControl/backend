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

@events.put("/event/cards_off_table/{game_id},{player_id}", status_code=200, tags=["Events"])
async def activate_cards_off_table_event(game_id: int, player_id: int, db: Session = Depends(get_db)):
    """
    Activa el evento 'Cards off the table': descarta las cartas not so fast de un jugador.
    """
    # Validar game_id
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found.")
    # Validar player_id
    player = db.query(Player).filter(Player.game_id == game_id, Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found.")
    
    result = cards_off_table(game_id=game_id, player_id=player_id, db=db)
    await broadcast_game_information(game_id)
    await broadcast_player_state(game_id)
    return result

@events.put("/event/look_into_ashes/{game_id},{player_id},{card_id}", status_code=200, tags=["Events"], response_model=Card_Response)
async def activate_look_into_ashes_event(game_id: int, player_id: int, card_id: int, db: Session = Depends(get_db)):
    """
    Activa el evento 'Look into the Ashes': un jugador toma una carta específica de la pila de descarte.
    """
    # Validar game_id
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found.")
    # Validar player_id
    player = db.query(Player).filter(Player.game_id == game_id, Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found.")
    # Validar card_id
    card = db.query(Card).filter(Card.game_id == game_id, Card.card_id == card_id, Card.dropped == True).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found.")
    
    taken_card = look_into_ashes(game_id=game_id, player_id=player_id, card_id=card_id, db=db)
    await broadcast_game_information(game_id)
    await broadcast_player_state(game_id)
    await broadcast_last_discarted_cards(player_id)
    return taken_card

@events.put("/event/one_more/{game_id},{receive_secret_player_id},{stealing_from_player_id},{secret_id}", status_code=200, tags=["Events"])
async def activate_one_more_event(game_id: int, receive_secret_player_id: int, stealing_from_player_id: int, secret_id: int, db: Session = Depends(get_db)):
    """
    Activa el evento 'One More': elige un secreto revelado y lo asigna boca abajo a otro jugador.
    """
    # Validar game_id
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found.")

    # Validar receive_secret_player_id
    receive_secret_player = db.query(Player).filter(Player.player_id == receive_secret_player_id, Player.game_id == game_id).first()
    if not receive_secret_player:
        raise HTTPException(status_code=404, detail="Receive secret Player not found in this game.")

    # Validar stealing_from_player_id
    stealing_from_player = db.query(Player).filter(Player.player_id == stealing_from_player_id, Player.game_id == game_id).first()
    if not stealing_from_player:
        raise HTTPException(status_code=404, detail="Stealing from Player not found in this game.")

    # Validar secret_id y que pertenezca al stealing_from_player y esté revelado
    secret = db.query(Secrets).filter(
        Secrets.secret_id == secret_id,
        Secrets.game_id == game_id,
        Secrets.player_id == stealing_from_player_id,
        Secrets.revelated == True  # Solo se pueden robar secretos revelados
    ).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found or is not revealed or does not belong to the stealing from player.")
    
    updated_secret = one_more(game_id=game_id, receive_secret_player_id=receive_secret_player_id, stealing_from_player_id=stealing_from_player_id, secret_id=secret_id, db=db)
    await broadcast_game_information(game_id)
    await broadcast_player_state(game_id)
    return updated_secret

@events.put("/event/early_train_paddington/{game_id}", status_code=200, tags=["Events"])
async def activate_early_train_paddington_event(game_id: int, db: Session = Depends(get_db)):
    """
    Activa el evento 'Early Train to Paddington': Toma hasta 6 cartas del mazo y las coloca boca arriba en la pila de descarte.
    """
    # Validar game_id
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found.")
    
    result = early_train_paddington(game_id=game_id, db=db)
    await broadcast_game_information(game_id)
    await broadcast_last_discarted_cards(game_id)
    return result

@events.put("/event/another_victim/{game_id},{new_player_id},{set_id}", status_code=200, tags=["Events"])
async def activate_another_victim_event(game_id: int, new_player_id: int, set_id: int, db: Session = Depends(get_db)):
    """
    Activa el evento 'Another Victim': Choose another victim for the 'Another Victim' event.
    """
    # Validar game_id
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found.")
    # Validar new_player_id
    new_player = db.query(Player).filter(Player.game_id == game_id, Player.id == new_player_id).first()
    if not new_player:
        raise HTTPException(status_code=404, detail="New Player not found.")
    # Validar set_id
    set = db.query(Set).filter(Set.game_id == game_id, Set.id == set_id).first()
    if not set:
        raise HTTPException(status_code=404, detail="Set not found.")
    
    result = another_victim(game_id=game_id, new_player_id=new_player_id, set_id=set_id, db=db)
    await broadcast_game_information(game_id)
    await broadcast_player_state(game_id)
    return result


