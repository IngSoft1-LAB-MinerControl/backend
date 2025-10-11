from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException, WebSocket
from sqlalchemy import desc, true
from sqlalchemy.orm import Session
from src.schemas.card_schemas import Card_Response
from src.database.database import SessionLocal
from src.database.models import Game, Player, Card
from src.schemas.games_schemas import Game_Response
from src.webSocket.connection_manager import lobbyManager, gameManager
from src.schemas.players_schemas import Player_Base, Player_State
import json 
from sqlalchemy.orm import joinedload

async def broadcast_available_games(db: Session):
    """
    Obtiene las partidas disponibles y las envía a todos los clientes conectados.
    """
    #games = db.query(Game).filter(
    #   (Game.status == "bootable") | (Game.status == "waiting players")
    #).all()

    games = db.query(Game).all()
    
    # 2. Conviertes cada objeto ORM a un objeto Pydantic Game_Response
    # Pydantic leerá los atributos (game.name, game.status, etc.) automáticamente
    gamesResponse = [Game_Response.model_validate(game) for game in games]
    
    # 3. Usas jsonable_encoder para convertir los objetos Pydantic a una
    # estructura de datos de Python compatible con JSON (listas de diccionarios)
    gamesResponseJson = jsonable_encoder(gamesResponse)

    
    # manager.broadcast espera un string, así que convertimos la lista a un JSON string.
    
    await lobbyManager.broadcast(json.dumps(gamesResponseJson))

async def broadcast_lobby_information (db:Session, game_id : int) :
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        # Si el juego ya no existe, no hacemos nada.
        print(f"Intento de broadcast para un juego no existente: {game_id}")
        return
    
    
    players = db.query(Player).filter(Player.game_id == game_id).all()
  
    gameResponse = Game_Response.model_validate(game).model_dump_json()
    playersResponse = [Player_Base.model_validate(player) for player in players]
    playersResponseJson = jsonable_encoder(playersResponse)
    await gameManager.broadcast(json.dumps({
        "type": "game",
        "data": gameResponse
    }), game_id)

    await gameManager.broadcast(json.dumps({
        "type": "players",
        "data": playersResponseJson
    }), game_id)

async def broadcast_game_information ( game_id : int) :
    db = SessionLocal()
    
    game = db.query(Game).filter(Game.game_id == game_id).first()
    if not game:
        # Si el juego ya no existe, no hacemos nada.
        print(f"Intento de broadcast para un juego no existente: {game_id}")
        return
    
    players = db.query(Player).options(
                        joinedload(Player.cards),joinedload(Player.secrets)).filter(Player.game_id == game_id).all()
    
    gameResponse = Game_Response.model_validate(game).model_dump_json()
    playersStateResponse = [Player_State.model_validate(player) for player in players]
    playersStateResponseJson = jsonable_encoder(playersStateResponse)

    await gameManager.broadcast(json.dumps({
        "type": "gameUpdated",
        "data": gameResponse
    }), game_id)

    await gameManager.broadcast(json.dumps({
        "type": "playersState",
        "data": playersStateResponseJson
    }), game_id)
        
        
async def broadcast_last_discarted_cards(player_id : int) : 
    db = SessionLocal() 
    player = db.query(Player).filter(Player.player_id == player_id).first()
    game_id = player.game_id
    cardsDropped = db.query(Card).filter(
        Card.game_id == game_id,
        Card.dropped == True
    ).order_by(desc(Card.discardInt)).limit(5).all()
    if not cardsDropped:
        raise HTTPException(status_code=404, detail="No cards found in the discard pile for this game.")
    
    #Actualizo la mano del jugador tambien
    players = db.query(Player).options(
                        joinedload(Player.cards),joinedload(Player.secrets)).filter(Player.game_id == game_id).all()
    playersStateResponse = [Player_State.model_validate(player) for player in players]
    playersStateResponseJson = jsonable_encoder(playersStateResponse)
    await gameManager.broadcast(json.dumps({
        "type": "playersState",
        "data": playersStateResponseJson
    }), game_id)
    
    cardsDroppedResponse = [Card_Response.model_validate(card) for card in cardsDropped]
    cardsResponseJson = jsonable_encoder(cardsDroppedResponse)
    await gameManager.broadcast(json.dumps({
        "type": "droppedCards",
        "data": cardsResponseJson
    }), game_id)
    




         
    