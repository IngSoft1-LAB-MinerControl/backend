from pydantic import BaseModel
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