from pydantic import BaseModel
from typing import Optional 

class Secret_Response(BaseModel): 
    secret_id : int
    player_id : Optional[int] = None
    game_id : int
    murderer : bool
    acomplice : bool
    revelated : bool
    class config:
        orm_mode = True