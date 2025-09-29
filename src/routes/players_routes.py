from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Game, Player 
from src.schemas.players_schemas import Player_Base
from src.database.services.services_games import update_players_on_game

player = APIRouter() # ahora el player es lo mismo que hacer app

#FALTA MANEJO  DE ERRORES por ids inexistentes de parametros, sobre todo que no haya internal server error (sucede al crear un player con un game id inexistente)
#Luego list players cuando le paso un game id inexistente no debe responder 200 sino que 404 NOT FOUND

#En general falta la estructura de si salta exception agarrarla y devolver el codigo correspondientev

@player.get ("/lobby/players/{game_id}", tags = ["Players"])
def list_players(game_id : int ,db: Session = Depends(get_db)):
    players = db.query(Player).filter(Player.game_id == game_id).all() # .all() me devuelve una lista, si no hay nada devuelve lista vacia
    if not players:
        raise HTTPException(status_code=404, detail="game not found or no players in this game")
    return players

@player.post("/players", status_code=201, tags = ["Players"])
def create_player(player : Player_Base, db: Session = Depends(get_db)):
    new_player = Player (name = player.name,
                            host = player.host,
                            game_id = player.game_id,
                            birth_date = player.birth_date)
    game = db.get(Game, new_player.game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    updated_game = update_players_on_game(new_player.game_id, db)
    if not updated_game:
        raise HTTPException(status_code=400, detail=f"Game already full")
    else:
        db.add(new_player)
        try:
            db.commit()
            db.refresh(new_player) #aca traigo el id generado por la db
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error creating player: {str(e)}")
    return new_player


@player.delete("/players/{player_id}", status_code=204,tags = ["Players"])
def delete_player(player_id: int, db:Session = Depends(get_db)):
    player = db.get(Player, player_id) 
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    try:
        db.delete(player)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting player: {str(e)}")
    return None

