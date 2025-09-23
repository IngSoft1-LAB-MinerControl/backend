from pydantic import BaseModel
from typing import Optional 
import datetime

class Player_Base(BaseModel): 
    id : Optional[int] = None 
    name : str
    host : bool 
    game_id : int 
    birth_date : datetime.date
    