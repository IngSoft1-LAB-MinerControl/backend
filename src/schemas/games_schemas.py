from pydantic import BaseModel
from typing import Optional 

class Game_Base(BaseModel) : 
    id : Optional[int] = None
    max_players : int 
    min_players : int
    status : str 
    name : str

class Game_Response (BaseModel) : 
    game_id : Optional[int] = None
    max_players : int 
    min_players : int
    status : str 
    name : str
    players_amount : int  
    current_turn : Optional[int] = None  
    cards_left : Optional[int] = None

class Game_Initialized (BaseModel) : 
    game_id : int 
    status : str 
    name : str 
    players_amount : int