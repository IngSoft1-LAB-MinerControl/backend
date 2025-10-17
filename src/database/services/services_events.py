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

def cards_off_table(game_id: int, player_id: int, db: Session):
    """
    descarta las cartas not so fast de un jugador
    """
    nsf = db.query(Event).filter(Event.name == "Not so fast", Event.game_id == game_id, Event.player_id == player_id, Event.dropped == False).all()

    if not nsf:
        # No hay cartas "Not so fast" para este jugador, no hay nada que hacer
        return {"message": "No 'Not so fast' cards found for this player to discard."}
    try:
        for event in nsf:
            event.dropped = True        
        db.commit() # se descartan las cartas nsf del jugador
    except Exception as e:
        db.rollback() 
        raise HTTPException(status_code=500, detail=f"Error discarding 'Not so fast' cards: {str(e)}")

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

def one_more(game_id: int, receive_secret_player_id: int, stealing_from_player_id: int, secret_id: int, db: Session):
    """
    Choose one revealed secret card and add it, face-down, to any player's secrets, 
    including your own. This may remove social disgrace.
    """
    try:
        stolen_secret = steal_secret_service(
            game_id=game_id,
            receive_secret_player_id=receive_secret_player_id, # El jugador que recibe el secreto
            stealing_from_player_id=stealing_from_player_id, # El jugador del que se "roba"
            secret_id=secret_id,
            db=db
        )
        return stolen_secret
    except HTTPException as e:
        # Re-lanzar excepciones específicas de steal_secret si es necesario
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error executing 'One More' event: {str(e)}")


# def delay_the_murderers_escape(game_id: int, player_id: int, cards_to_return_ids: List[int], db: Session):
#     """
#     Implementa el efecto de la carta 'Delay the Murderer's Escape!'.
#     Toma hasta 5 cartas de la pila de descarte y las devuelve al mazo.
#     La carta de evento se retira del juego.
#     """
#     # 2. Obtener las cartas de la pila de descarte a devolver al mazo
#     if len(cards_to_return_ids) > 5:
#         raise HTTPException(status_code=400, detail="Cannot return more than 5 cards to the draw pile.")
    
#     cards_to_return = db.query(Card).filter(
#         Card.card_id.in_(cards_to_return_ids),
#         Card.game_id == game_id,
#         Card.dropped == True, # Debe estar en la pila de descarte
#     ).all()

#     if len(cards_to_return) != len(cards_to_return_ids):
#         raise HTTPException(status_code=404, detail="One or more selected cards not found in the discard pile or are not available.")

#     # 3. Restablecer el estado de las cartas seleccionadas y devolverlas al mazo
#     game = db.query(Game).filter(Game.game_id == game_id).first()
#     if not game:
#         raise HTTPException(status_code=404, detail="Game not found.")

#     for card in cards_to_return:
#         card.dropped = False
#         card.picked_up = False
#         card.player_id = None
#         card.discardInt = 0 # Reiniciar el orden de descarte
#         card.draft = False # Asegurarse de que no esté en el draft pile
#     try:
#         db.commit()
#         db.refresh(game)
#         for card in cards_to_return:
#             db.refresh(card)
#         return {"message": "Cards returned to draw pile and event card removed from game."}
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Error executing 'Delay the Murderer's Escape!': {str(e)}")


def another_victim(game_id: int, new_player_id: int, set_id: int, db: Session):
    """
    Choose another victim for the 'Another Victim' event.
    """
    set = db.query(Set).filter(Set.game_id == game_id, Set.set_id == set_id).first()

    if not set:
        raise HTTPException(status_code=404, detail="Set not found.")
    set.player_id = new_player_id
    try:
        db.commit()
        db.refresh(set)
        return {"message": "set has new owner."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error executing 'Another Victim' event: {str(e)}")

def early_train_paddington(game_id: int, db: Session):
    """
    Implement the effect of the 'Early Train to Paddington' event.
    """
    deck = db.query(Card).filter(Card.game_id == game_id, Card.player_id == None, Card.draft == False).all()
    
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found.")
    
    if len(deck)<6:
        finish_game(game_id) # se termina el juego si no hay mas cartas en el mazo
        return {"message": "Not enough cards in the deck. The game has ended."}
    
    random.shuffle(deck)
    max_discardInt = db.query(func.max(Card.discardInt)).filter(Card.game_id == game_id).scalar() or 0
    for card in deck[:6]:
        card.dropped = True
        card.picked_up = False
        max_discardInt += 1
        card.discardInt = max_discardInt # Asigna el siguiente valor en la secuencia
    try:
        db.commit()
        db.refresh(deck)
        return {"message": "Early Train to Paddington event executed successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error executing 'Early Train to Paddington' event: {str(e)}")
