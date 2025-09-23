from pydantic import BaseModel
from typing import Optional 

class Game_Base(BaseModel) : 
    id : Optional[int] = None
    max_players : int 
    min_players : int
    status : str 
    name : str 
