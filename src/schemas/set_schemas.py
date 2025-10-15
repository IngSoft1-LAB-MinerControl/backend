from pydantic import BaseModel, ConfigDict
from typing import Optional, Union 
from src.schemas.card_schemas import  Detective_Response

class Set_Base(BaseModel) : 
    set_id : int 
    name : str 
    game_id : int
    player_id : int 

    class config:
        orm_mode = True
    model_config = ConfigDict(from_attributes=True) 

class Set_Response(Set_Base) : 
    detective : list [Detective_Response]
    model_config = ConfigDict(from_attributes= True)

    