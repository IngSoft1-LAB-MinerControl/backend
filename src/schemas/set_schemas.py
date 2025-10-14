from pydantic import BaseModel, ConfigDict
from typing import Optional, Union 

class Set_Response(BaseModel) : 
    set_id : int 
    name : str 
    game_id : int
    player_id : int 

    class config:
        orm_mode = True
    model_config = ConfigDict(from_attributes=True) 

    