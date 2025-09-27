from fastapi import FastAPI
from src.routes.players_routes import player
from src.routes.games_routes import game
from src.routes.cards_routes import card
app = FastAPI()

@app.get("/")
def hola() :
    return "Hola Mundo"
 
app.include_router(player)
app.include_router(game)
app.include_router(card)

