from pydantic import BaseModel, ConfigDict
from typing import Optional 

class Card_Response(BaseModel): 
    card_id : int
    player_id : Optional[int] = None
    game_id : int
    picked_up : bool
    dropped : bool
    type : str
    class config:
        orm_mode = True
    model_config = ConfigDict(from_attributes=True)    