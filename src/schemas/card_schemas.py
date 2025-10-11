from pydantic import BaseModel, ConfigDict
from typing import Optional 

class Card_Response(BaseModel): 
    card_id : int
    player_id : Optional[int] = None
    game_id : int
    picked_up : bool
    dropped : bool
    type : str
    draft: bool
    discardInt: int
    class config:
        orm_mode = True
    model_config = ConfigDict(from_attributes=True)    

class Detective_Response(Card_Response): 
    name : str
    detective_id : int
    quantity_set : int
    set_id : Optional[int] = None

class Event_Response(Card_Response): 
    name : str
    event_id : int
   