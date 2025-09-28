from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Secrets, Player
import random

def deal_secrets_to_players(game_id: int, db: Session):
    """
    Reparte 3 secretos aleatorios a cada jugador en una partida específica.
    """
    # Obtener todos los jugadores de la partida.
    players = db.query(Player).filter(Player.game_id == game_id).all()
    num_players = len(players)

    # Obtener todos los secretos disponibles (las que no tienen un player_id asignado).
    secrets_deck = db.query(Secrets).filter(Secrets.game_id == game_id, Secrets.player_id == None).all()
    if len(secrets_deck) < num_players * 3: 
        raise HTTPException(status_code=400, detail="los secretos ya han sido repartidas en esta partida.")

    # se supone que esto se llama cuando arranca la partida asiq todo va a estar en None

    #se podria chequear con la cantidad de cartas y ver que el tamano de la lista 
    # y cartas sea la misma, sino error

    # barajar las cartas 
    random.shuffle(secrets_deck)

    try:
        # Asignar 3 secretos a cada jugador.
        secret_cursor = 0
        for player in players:
            for _ in range(3): # Repartir 3 secretos
                secret_to_deal = secrets_deck[secret_cursor]
                # Asignar el secreto al jugador (asignar un secreto es cambiarle el player_id y poner picked_up en True)
                secret_to_deal.player_id = player.player_id
                secret_cursor += 1
        # Confirmar todos los cambios en la base de datos
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ocurrió un error al repartir los secretos: {str(e)}")

    return {"message": f"Se repartieron 3 secretos a {num_players} jugadores en la partida {game_id}."}

def init_secrets(game_id : int , db: Session = Depends(get_db)):
    new_secret_list = []
    players = db.query(Player).filter(Player.game_id == game_id).all()
    num_players = len(players)

    for _ in range(num_players*3): 
        new_secret = Secrets(murderer = False ,
                            acomplice = False ,
                            revelated = False ,
                            player_id = None,
                            game_id= game_id)
        new_secret_list.append(new_secret)

    try:
        db.add_all(new_secret_list)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating cards: {str(e)}")

    return {"message": f"{num_players*3} secrets created successfully"}
