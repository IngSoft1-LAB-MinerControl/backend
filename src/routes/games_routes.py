from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Game 
from src.schemas.games_schemas import Game_Base, Game_Response
from src.database.services.services_games import assign_turn_to_players
from src.database.services.services_cards import init_cards, deal_cards_to_players
from src.database.services.services_secrets import init_secrets


game = APIRouter()

@game.get("/games")
def list_games (db: Session = Depends(get_db)) :
    return db.query(Game).all()

@game.get("/games/availables")
def list_available_games (db : Session = Depends (get_db)): 
    return db.query(Game).filter((Game.status == "bootable") |  (Game.status == "waiting players")).all()

@game.post ("/games", status_code=201, response_model = Game_Response) #devolvia un int y queria devolver una response con el schema de game_base
def create_game (game : Game_Base, db: Session = Depends(get_db)) : 
    new_game = Game (status = game.status,
                        max_players = game.max_players,
                        min_players = game.min_players,
                        name = game.name,
                        players_amount = 0)
    db.add(new_game)
    try:
        db.commit()
        db.refresh(new_game)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating game: {str(e)}")
    return new_game


@game.delete("/game/{game_id}", status_code=204)
def delete_game(game_id: int, db:Session = Depends(get_db)):
    game = db.get(Game, game_id) 
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    try:
        db.delete(game)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting game: {str(e)}")
    return None



@game.post("/game/beginning/{game_id}", status_code = 202 ) 
def initialize_game (game_id : int, db : Session = Depends(get_db)):
    turns_assigned = assign_turn_to_players (game_id, db)
    cards_initialized = init_cards (game_id, db)
    secrets_initialized = init_secrets(game_id, db)
    cards_dealt = deal_cards_to_players (game_id, db)




    return {"Message : Juego inicializado"}

