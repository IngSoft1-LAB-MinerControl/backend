from fastapi import FastAPI
from src.routes.players_routes import player
from src.routes.games_routes import game
from src.routes.cards_routes import card
from src.routes.secrets_routes import secret
from src.routes.websocket_routes import ws
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title = "Agatha Christie's Death on the Cards API ",
    description = "API to connect with server for the respective game"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Podés poner la URL de tu frontend: ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, PUT, DELETE, OPTIONS
    allow_headers=["*"],  # Authorization, Content-Type, etc.
)




@app.get("/")
def hola() :
    return "Hola Mundo"

app.include_router(ws) 
app.include_router(player)
app.include_router(game)
app.include_router(card)
app.include_router(secret)


