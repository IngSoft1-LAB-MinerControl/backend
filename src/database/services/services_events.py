import random
from fastapi import Depends
from sqlalchemy import desc, func
from src.database.database import SessionLocal, get_db
from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.database.models import Player, Card , Detective , Event, Secrets, Game, Set
from src.database.services.services_games import finish_game
from src.database.services.services_secrets import steal_secret as steal_secret_service
from typing import List 


def look_into_ashes(player_id: int, card_id: int, db: Session):
    """
    mira las ultimas 5 cartas de la pila de descarte y toma una 
    en realidad le llega una card_id del front que. esta la funcion que le muestra las 5 
    cartas del descarte. entonces en el endpoint que llama esta funcion solo elije una de esas 5 cartas
    y le cambio dueno y dropped por true
    """
    card = db.query(Card).filter(Card.card_id == card_id, Card.dropped == True).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found.")
    try:
        card.dropped = False
        card.player_id = player_id
        card.discardInt = 0 #la carta vuelve a estar en juego
        card.picked_up=True
        db.commit()
        db.refresh(card)
        return card 
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error assigning card to player: {str(e)}")
