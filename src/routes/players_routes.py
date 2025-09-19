from fastapi import APIRouter, Depends  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from database.database import SessionLocal, get_db
from modelos.modelos import Jugador 
from schemas.players_schemas import Jugador_Base 

player = APIRouter() # ahora el player es lo mismo que hacer app

@player.get ("/lobby/players")
def list_players(db: Session = Depends(get_db)):
    return db.query(Jugador).all()

@player.post("/players")
def create_player(jugador : Jugador_Base, db: Session = Depends(get_db)):
    nuevo_jugador = Jugador (nombre = jugador.nombre,
                            es_anfitrion = jugador.es_anfitrion
    )
    db.add(nuevo_jugador)
    db.commit()
    db.refresh(nuevo_jugador) #aca traigo el id generado por la db 
    return nuevo_jugador

