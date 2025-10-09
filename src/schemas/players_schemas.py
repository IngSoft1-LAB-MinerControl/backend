from pydantic import BaseModel, ConfigDict
from typing import Optional 
import datetime

class Player_Base(BaseModel): 
    player_id : Optional[int] = None 
    name : str
    host : bool 
    game_id : int 
    birth_date : datetime.date
    model_config = ConfigDict(from_attributes=True)    
