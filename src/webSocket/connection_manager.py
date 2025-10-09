from collections import defaultdict
from typing import List, Dict
from fastapi import APIRouter, WebSocket 

ws = APIRouter()

class ConnectionManagerLobby: # ESTE MANEJA LA LISTA DE PARTIDAS DISPONIBLES
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

lobbyManager = ConnectionManagerLobby()



class ConnectionManagerGames :  # ESTE MANEJA SALA DE ESPERA Y PARTIDA EN JUEGO
    def __init__(self): 
        self.active_connections : Dict[int, List[WebSocket]] = defaultdict(list)

    async def connect (self, websocket : WebSocket, game_id : int) : 
        await websocket.accept() 
        self.active_connections[game_id].append(websocket)
    def disconnect (self, websocket : WebSocket, game_id : int) : 
        self.active_connections[game_id].remove(websocket)
        if not self.active_connections[game_id]:
            del self.active_connections[game_id]

    async def broadcast (self, message : str, game_id : int) : 
        for connection in self.active_connections[game_id]: 
            await connection.send_text(message)   

gameManager = ConnectionManagerGames() 