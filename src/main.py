from fastapi import FastAPI
from src.routes.players_routes import player
from src.routes.games_routes import game
from src.routes.cards_routes import card
from src.routes.secrets_routes import secret
app = FastAPI()

@app.get("/")
def hola() :
    return "Hola Mundo"
 
app.include_router(player)
app.include_router(game)
app.include_router(card)
app.include_router(secret)


