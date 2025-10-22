from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func  
from src.database.database import SessionLocal, get_db
from src.database.models import Card , Game , Detective , Event
from src.database.services.services_cards import only_6 , replenish_draft_pile
from src.database.services.services_games import finish_game
from src.schemas.card_schemas import Card_Response , Detective_Response , Event_Response, Discard_List_Request
from src.database.services.services_websockets import broadcast_last_discarted_cards, broadcast_game_information , broadcast_player_state, broadcast_card_draft
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

@card.get("/lobby/list/detectives/{player_id}", tags=["Cards"], response_model=list[Detective_Response])
def list_detectives_ofplayer(player_id: int, db: Session = Depends(get_db)):
    cards = db.query(Detective).filter(Detective.player_id == player_id, Detective.dropped == False).all()
    if not cards:
        raise HTTPException(status_code=404, detail="No cards found for the given player_id")
    return cards

@card.get("/lobby/list/events/{player_id}", tags=["Cards"], response_model=list[Event_Response])
def list_events_ofplayer(player_id: int, db: Session = Depends(get_db)):
    cards = db.query(Event).filter(Event.player_id == player_id, Event.dropped == False).all()
    if not cards:
        raise HTTPException(status_code=404, detail="No cards found for the given player_id")
    return cards

@card.put("/cards/pick_up/{player_id},{game_id}", status_code=200, tags=["Cards"], response_model=Card_Response)
async def pickup_a_card(player_id: int, game_id: int, db: Session = Depends(get_db)):
    has_6_cards = only_6(player_id, db)
    if has_6_cards:
        raise HTTPException(status_code=400, detail="The player already has 6 cards")
    delayed_card = db.query(Card).filter(Card.game_id == game_id, Card.discardInt == -1, Card.dropped == False, Card.picked_up == False, Card.draft == False).first()
    if delayed_card : 
        card = delayed_card
    deck = db.query(Card).filter(Card.game_id == game_id, Card.dropped == False , Card.picked_up == False , Card.draft == False).all()
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not delayed_card : 
        random.shuffle(deck)
        if not deck: 
            await finish_game(game_id, db)
            raise HTTPException(status_code=400, detail="The player already has 6 cards")

        if game.cards_left is None:
            await finish_game(game_id, db)
        card = deck[0]
    try:
        card.picked_up = True
        card.player_id = player_id
        game.cards_left = len(deck) -1
        if game.cards_left == 0:
            await finish_game(game_id, db)
        db.commit()
        db.refresh(card)
        db.refresh(game)
        await broadcast_game_information(game_id)
        return card
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error assigning card to player: {str(e)}")


@card.put("/cards/drop/{player_id}" , status_code=200, tags = ["Cards"], response_model=Card_Response)
async def discard_card(player_id : int , db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.player_id == player_id , Card.dropped == False).first()
    if not card:
        raise HTTPException(status_code=404, detail="All cards dropped")       
    try:
        # Encuentra el valor máximo actual de discardInt en la partida
        max_discard = db.query(func.max(Card.discardInt)).filter(Card.game_id == card.game_id).scalar()
        
        # Asigna el siguiente valor en la secuencia
        card.discardInt = (max_discard or 0) + 1
        
        card.dropped = True
        card.picked_up = False
        db.commit()
        db.refresh(card)
        await broadcast_last_discarted_cards(player_id)
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
        # Encuentra el valor máximo actual de discardInt en la partida
        max_discard = db.query(func.max(Card.discardInt)).filter(Card.game_id == card.game_id).scalar()

        # Asigna el siguiente valor en la secuencia
        card.discardInt = (max_discard or 0) + 1

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

@card.put("/cards/draft_pickup/{game_id},{card_id},{player_id}", status_code=200, tags=["Cards"], response_model=Card_Response)
async def pick_up_draft_card(game_id: int, card_id: int, player_id: int, db: Session = Depends(get_db)):
    card = db.query(Card).filter(Card.card_id == card_id, Card.game_id == game_id, Card.draft == True).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found in draft pile.")
    if only_6(player_id, db):
        raise HTTPException(status_code=400, detail="The player already has 6 cards")    
    try:
        card.draft = False
        card.player_id = player_id
        card.picked_up=True
        replenish_draft_pile(game_id, db)

        db.commit()
        db.refresh(card)
        await broadcast_game_information(game_id)
        await broadcast_card_draft(game_id)
        return card
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error picking up card: {str(e)}")

@card.get("/cards/discard-pile/{game_id}", tags=["Cards"], response_model=list[Card_Response])
def get_top_discard_pile(game_id: int, db: Session = Depends(get_db)):
    """
    Obtiene las últimas 5 cartas de la pila de descarte, ordenadas de la más reciente a la más antigua.
    """
    discarded_cards = db.query(Card).filter(
        Card.game_id == game_id,
        Card.dropped == True
    ).order_by(desc(Card.discardInt)).limit(5).all()

    if not discarded_cards:
        raise HTTPException(status_code=404, detail="No cards found in the discard pile for this game.")
    
    return discarded_cards
@card.put("/cards/game/drop_list/{player_id}" , status_code=200, tags = ["Cards"], response_model=list[Card_Response])
async def select_cards_to_discard(player_id: int, discard_request: Discard_List_Request, db: Session = Depends(get_db)):
    card_ids = discard_request.card_ids
    
    if not card_ids:
        raise HTTPException(status_code=400, detail="Se requiere una lista de IDs de cartas.")

    # Se buscan todas las cartas que el jugador quiere descartar
    cards_to_discard = db.query(Card).filter(
        Card.player_id == player_id,
        Card.dropped == False,
        Card.card_id.in_(card_ids)
    ).all()
    
    # validación
    if len(cards_to_discard) != len(card_ids):
        # Esto indica que una o más de las cartas en la lista no cumplían los filtros
        raise HTTPException(
            status_code=403, 
            detail="Una o más cartas seleccionadas no están en la mano del jugador o ya fueron descartadas."
        )

    try:
        # 3. ENCONTRAR EL MÁXIMO discardInt
        max_discard = db.query(func.max(Card.discardInt)).filter(Card.game_id == cards_to_discard[0].game_id).scalar()
        next_discard_int = (max_discard or 0) + 1
        
        updated_cards = []

        # 4. ITERAR Y ACTUALIZAR
        for card_obj in cards_to_discard:
            card_obj.discardInt = next_discard_int
            card_obj.dropped = True
            card_obj.picked_up = False
            updated_cards.append(card_obj)
            next_discard_int += 1
        
        db.commit()

        # 5. REFRESCAR Y RETORNAR (Uniformidad: refrescamos los objetos)
        # Refrescamos los objetos para asegurarnos de que el ORM tenga los valores correctos
        for card_obj in updated_cards:
             db.refresh(card_obj)

        # 6. BROADCAST (La parte clave para que desaparezcan del frontend)
        await broadcast_last_discarted_cards(player_id)
        
        return updated_cards
        
    except Exception as e:
        db.rollback()
        # Puedes añadir un manejo de HTTPException para uniformidad si no lo hiciste en el paso 2
        raise HTTPException(status_code=500, detail=f"Error al descartar cartas seleccionadas: {str(e)}")