from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Secrets, Player
import random

def deal_secrets_to_players(game_id: int, db: Session):
    """
    Reparte 3 secretos aleatorios a cada jugador, reintentando si el Asesino y
    el Cómplice son el mismo jugador.
    """
    players = db.query(Player).filter(Player.game_id == game_id).all()
    num_players = len(players)
    secrets_deck = db.query(Secrets).filter(Secrets.game_id == game_id, Secrets.player_id.is_(None)).all()

    if len(secrets_deck) < num_players * 3:
        raise HTTPException(status_code=400, detail="No hay suficientes secretos para repartir o ya fueron repartidos.")

    while True:
        # 1. Barajar las cartas en cada intento
        random.shuffle(secrets_deck)

        # 2. Asignar 3 secretos a cada jugador
        secret_cursor = 0
        for player in players:
            for _ in range(3):
                secret_to_deal = secrets_deck[secret_cursor]
                secret_to_deal.player_id = player.player_id
                secret_cursor += 1

        # 3. Comprobar la condición
        murderer_card = next((s for s in secrets_deck if s.murderer), None)
        acomplice_card = next((s for s in secrets_deck if s.acomplice), None)

        # Si no hay cómplice o si los dueños son diferentes, la repartición es válida
        if not acomplice_card or (acomplice_card.player_id != murderer_card.player_id):
            break  # Salir del bucle while

        # Si la condición no se cumple, el bucle se repetirá, volviendo a barajar y asignar.

    try:
        # 4. Confirmar los cambios en la base de datos una vez que la repartición es válida
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ocurrió un error al repartir los secretos: {str(e)}")

    return {"message": f"Se repartieron 3 secretos a {num_players} jugadores en la partida {game_id}."}

def init_secrets(game_id : int , db: Session = Depends(get_db)):
    new_secret_list = []
    players = db.query(Player).filter(Player.game_id == game_id).all()
    num_players = len(players)

    cards_to_create = num_players * 3 - 1 # una carta es la del asesino
    # Cada jugador recibe 3 secretos, por lo que se crean 3 * número de jugadores
    if num_players > 4: 
        cards_to_create = cards_to_create - 1 # si hay mas de 4 jugadores un secreto va a ser el del complice
        acomplice_card = Secrets(murderer=False, acomplice=True, revelated=False, player_id=None, game_id=game_id)
        new_secret_list.append(acomplice_card)
    # 
    murderer_card = Secrets(murderer=True, acomplice=False, revelated=False, player_id=None, game_id=game_id)
    new_secret_list.append(murderer_card)

    for _ in range(cards_to_create):
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

    return {"message": f"{len(new_secret_list)} secrets created successfully"}
