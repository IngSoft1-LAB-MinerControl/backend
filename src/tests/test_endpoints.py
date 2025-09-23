
from fastapi.testclient import TestClient 
from src.main import app 


client = TestClient (app)

def test_create_games () : 
    parameters = {"max_players" : 6, "min_players" : 2, "status" :  "esperando a jugadores", "name" : "Luca's Lobby"}
    response = client.post(
        "/games", json = parameters)
    assert response.status_code == 200
    data = response.json() 
    assert data["max_players"] == 6
    assert data["min_players"] == 2
    assert data["status"] == "esperando a jugadores"
    assert data["name"] == "Luca's Lobby" 



