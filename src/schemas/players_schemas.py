from pydantic import BaseModel, ConfigDict
from typing import Optional 
import datetime
from src.schemas.card_schemas import Card_Response
from src.schemas.secret_schemas import Secret_Response

class Player_Base(BaseModel): 
    player_id : Optional[int] = None 
    name : str
    host : bool 
    game_id : int 
    birth_date : datetime.date
    model_config = ConfigDict(from_attributes=True)    


class Player_State(Player_Base) : 
    turn_order : int
    cards : list[Card_Response]
    secrets : list[Secret_Response]
    