from fastapi import APIRouter, Depends  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Player 
from src.schemas.players_schemas import Player_Base 

player = APIRouter() # ahora el player es lo mismo que hacer app

#FALTA MANEJO  DE ERRORES por ids inexistentes de parametros, sobre todo que no haya internal server error (sucede al crear un player con un game id inexistente)
#Luego list players cuando le paso un game id inexistente no debe responder 200 sino que 404 NOT FOUND

#En general falta la estructura de si salta exception agarrarla y devolver el codigo correspondientev

@player.get ("/lobby/players/{game_id}")
def list_players(game_id : int ,db: Session = Depends(get_db)):
    #Falta completar listar players por game id
     
    return db.query(Player).filter( Player.game_id == game_id).all()

@player.post("/players")
def create_player(player : Player_Base, db: Session = Depends(get_db)):
    new_player = Player (name = player.name,
                            host = player.host,
                            game_id = player.game_id ,
                            birth_date = player.birth_date
                        )
    db.add(new_player)
    db.commit()
    db.refresh(new_player) #aca traigo el id generado por la db 
    return new_player


@player.delete("/players/{player_id}")
def delete_player(player_id: int, db:Session = Depends(get_db)):
    player = db.get(Player, player_id) 
    print (player)
    try:
        db.delete(player)
        db.commit()
    except Exception:
        db.rollback()
    return player


