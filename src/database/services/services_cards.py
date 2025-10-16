import random
from fastapi import Depends
from src.database.database import SessionLocal, get_db
from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.database.models import Player, Card , Detective , Event, Game

def setup_initial_draft_pile(game_id: int, db: Session):
    """
    Selecciona las primeras 3 cartas del mazo para formar el draft pile inicial.
    """
    deck = db.query(Card).filter(
        Card.game_id == game_id, 
        Card.player_id.is_(None),
        Card.draft == False
    ).all()
    random.shuffle(deck)

    for card in deck[:3]: # solo lo hace 3 veces 
        card.draft = True
    
    # El commit se hará en la ruta que llama a esta función.
    return {"message": "Initial draft pile created successfully."}

def replenish_draft_pile(game_id: int, db: Session):
    """
    Repone una carta en el draft pile desde el mazo principal.
    """
    game = db.query(Game).filter(Game.game_id == game_id).first()
    deck = db.query(Card).filter(
        Card.game_id == game_id,
        Card.player_id.is_(None),
        Card.draft == False
    ).all()
    random.shuffle(deck)
     
    deck[0].draft = True
    game.cards_left = game.cards_left -1
    # Si no hay cartas, el draft pile simplemente se achicará. No es un error.
    return deck[0] if deck else None

def deal_cards_to_players(game_id: int, db: Session):
    """
    Reparte 6 cartas aleatorias a cada jugador en una partida específica.
    """
    # Obtener todos los jugadores de la partida.
    players = db.query(Player).filter(Player.game_id == game_id).all()
    num_players = len(players)

    # Obtener todas las cartas disponibles (las que no tienen un player_id asignado).
   
    nsf = db.query(Event).filter(Event.name == "Not so fast").all()
    # se supone que esto se llama cuando arranca la partida asiq todo va a estar en None

    #se podria chequear con la cantidad de cartas y ver que el tamano de la lista 
    # y cartas sea la misma, sino error

    # barajar las cartas 
    
    random.shuffle(nsf)
    try:
        # Asignar 6 cartas a cada jugador.
        card_cursor = 0
        nsf_cursor = 0
        for player in players:
            nsf_to_deal = nsf[nsf_cursor] #Repartir 1 nsf a cada jugador
            nsf_to_deal.player_id = player.player_id
            nsf_to_deal.picked_up = True
            nsf_cursor += 1
        deck = db.query(Card).filter(Card.game_id == game_id, Card.player_id == None).all()
        random.shuffle(deck)
        
        for player in players : 
            for _ in range(5): # Repartir 5 cartas
                card_to_deal = deck[card_cursor]
                # Asignar la carta al jugador (asignar una carta es cambiarle el player_id y poner picked_up en True)
                card_to_deal.player_id = player.player_id
                card_to_deal.picked_up = True
                card_cursor += 1
        # Confirmar todos los cambios en la base de datos
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ocurrió un error al repartir las cartas: {str(e)}")

    return {"message": f"Se repartieron 6 cartas a {num_players} jugadores en la partida {game_id}."}


def init_detective_cards(game_id: int, db: Session = Depends(get_db)):
    detectives_info = [
        ("Harley Quin Wildcard", 4 , 1),
        ("Adriane Oliver", 3 , 1),
        ("Miss Marple", 3 , 3),
        ("Parker Pyne", 3 , 2),
        ("Tommy Beresford", 2 , 2),
        ("Lady Eileen 'Bundle' Brent", 3 , 2),
        ("Tuppence Beresford", 2 , 2),
        ("Hercule Poirot", 3 , 3),
        ("Mr Satterthwaite", 2 , 2),
    ]

    new_cards_list = []
    for name, quantity, quantity_set in detectives_info:
        for _ in range(quantity):
            new_card_instance = Detective(
                type="detective",
                name=name,
                picked_up=False,
                dropped=False,
                player_id=None,
                game_id=game_id,
                quantity_set = quantity_set,
                set_id = None,

            )
            new_cards_list.append(new_card_instance)

    try:
        db.add_all(new_cards_list)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating detective cards: {str(e)}")
    
    return {"message": f"{len(new_cards_list)} detective cards created successfully"}

def init_event_cards(game_id: int, db: Session = Depends(get_db)):
    events_info = [
        ("Delay the murderer's escape!", 3),
        ("Point your suspicions", 3),
        ("Dead card folly", 3),
        ("Another Victim", 2),
        ("Look into the ashes", 3),
        ("Card trade", 3),
        ("And then there was one more...", 2),
        ("Early train to paddington", 2),
        ("Cards off the table", 1),
        ("Not so fast" , 10) ,
        ("Social Faux Pas" , 3) ,
        ("Blackmailed" , 1)
    ]

    new_events_list = []
    for name, quantity in events_info:
        for _ in range(quantity):
            new_event_instance = Event(
                type="event",
                name=name,
                picked_up=False,
                dropped=False,
                player_id=None,
                game_id=game_id
            )
            new_events_list.append(new_event_instance)

    try:
        db.add_all(new_events_list)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating event cards: {str(e)}")
    
    return {"message": f"{len(new_events_list)} event cards created successfully"}


def only_6 (player_id , db: Session = Depends(get_db)):
    cartas_levantadas = db.query(Card).filter(
        Card.player_id == player_id,
        Card.picked_up == True,
        Card.dropped == False
    ).count()
    if cartas_levantadas >= 6:
        return True
    else:
        return False
