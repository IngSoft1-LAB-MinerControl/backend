from fastapi import APIRouter, Depends, HTTPException, WebSocket  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Game 
from src.schemas.games_schemas import Game_Base, Game_Response, Game_Initialized
from src.database.services.services_games import assign_turn_to_players
from src.database.services.services_cards import init_cards, deal_cards_to_players
from src.database.services.services_secrets import init_secrets, deal_secrets_to_players
from src.database.services.services_websockets import broadcast_available_games
from src.webSocket.connection_manager import manager  


game = APIRouter()



@game.websocket("/ws/games/availables", name="ws_available_games")
async def ws_available_games(websocket: WebSocket, db: Session = Depends(get_db)):
    await manager.connect(websocket)
    # Envía la lista actual de partidas tan pronto como el cliente se conecta
    await broadcast_available_games(db)
    try:
        while True:
            # Mantenemos la conexión abierta. 
            # El receive_text es solo para detectar cuando el cliente se desconecta.
            await websocket.receive_text()
    except Exception:
        # Cuando el cliente se desconecta, se lanza una excepción
        manager.disconnect(websocket)
        # Opcional: podrías notificar a los demás si fuera necesario, 
        # pero para una lista de partidas no hace falta.

@game.get("/games",tags = ["Games"])
def list_games (db: Session = Depends(get_db)) :
    return db.query(Game).all()

@game.get("/games/availables",tags = ["Games"])
def list_available_games (db : Session = Depends (get_db)): 
    return db.query(Game).filter((Game.status == "bootable") |  (Game.status == "waiting players")).all()

@game.post ("/games", status_code=201, response_model = Game_Response,tags = ["Games"]) #devolvia un int y queria devolver una response con el schema de game_base
async def create_game (game : Game_Base, db: Session = Depends(get_db)) : 
    new_game = Game (status = game.status,
                        max_players = game.max_players,
                        min_players = game.min_players,
                        name = game.name,
                        players_amount = 0)
    db.add(new_game)
    try:
        db.commit()
        db.refresh(new_game)
        await broadcast_available_games(db)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating game: {str(e)}")
    return new_game


@game.delete("/game/{game_id}", status_code=204, tags = ["Games"])
async def delete_game(game_id: int, db:Session = Depends(get_db)):
    game = db.get(Game, game_id) 
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    try:
        db.delete(game)
        db.commit()
        await broadcast_available_games(db)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting game: {str(e)}")
    return None



@game.post("/game/beginning/{game_id}", status_code = 202,response_model= Game_Initialized, tags = ["Games"] ) 
def initialize_game (game_id : int, db : Session = Depends(get_db)):
    game = db.query(Game).where(Game.game_id == game_id).first()
    if game.players_amount >= game.min_players :  
        turns_assigned = assign_turn_to_players (game_id, db)
        cards_initialized = init_cards (game_id, db)
        secrets_initialized = init_secrets(game_id, db)
        cards_dealt = deal_cards_to_players (game_id, db)
        secrets_dealt = deal_secrets_to_players (game_id, db)
        game.status = "in course"
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error updating turn's game: {str(e)}")
    else : 
        raise HTTPException(status_code=424, detail=f"Error, you need more players to start game")
    return game

@game.put ("/game/update_turn/{game_id}", status_code = 202, tags = ["Games"])
def update_turn (game_id : int , db: Session = Depends(get_db)) : 
    game = db.query(Game).where(Game.game_id == game_id).first()
    if game.current_turn < game.players_amount : 
        game.current_turn += 1 
    else : 
        game.current_turn = 1
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error updating turn's game: {str(e)}")

    return game.current_turn

@game.get("/games/{game_id}", tags=["Games"])
def get_game(game_id: int, db: Session = Depends(get_db)):
    game = db.get(Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game