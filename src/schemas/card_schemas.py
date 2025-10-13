from pydantic import BaseModel, ConfigDict
from typing import Optional, Union 

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
    quantity_set : int
    set_id : Optional[int] = None
    class config:
        orm_mode = True
    model_config = ConfigDict(from_attributes=True)    

class Event_Response(Card_Response): 
    name : str
    class config:
        orm_mode = True
    model_config = ConfigDict(from_attributes=True)    

AllCardsResponse = Union[Detective_Response, Event_Response]


   