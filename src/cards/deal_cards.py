import random
from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.database.models import Player, Card

def deal_cards_to_players(game_id: int, db: Session):
    """
    Reparte 6 cartas aleatorias a cada jugador en una partida específica.
    """
    # Obtener todos los jugadores de la partida.
    players = db.query(Player).filter(Player.game_id == game_id).all()
    num_players = len(players)

    # Obtener todas las cartas disponibles (las que no tienen un player_id asignado).
    deck = db.query(Card).filter(Card.game_id == game_id, Card.player_id == None).all()
    # se supone que esto se llama cuando arranca la partida asiq todo va a estar en None

    #se podria chequear con la cantidad de cartas y ver que el tamano de la lista 
    # y cartas sea la misma, sino error

    # barajar las cartas 
    random.shuffle(deck)

    try:
        # Asignar 6 cartas a cada jugador.
        card_cursor = 0
        for player in players:
            for _ in range(6): # Repartir 6 cartas
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