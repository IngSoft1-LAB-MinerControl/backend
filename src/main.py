from fastapi import FastAPI
from src.routes.players_routes import player
from src.routes.games_routes import game
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

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
 
app.include_router(player)
app.include_router(game)
