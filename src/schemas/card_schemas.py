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

class Discard_List_Request(BaseModel):
    #Esquema para recibir una lista de IDs de cartas a descartar
    card_ids: list[int]

    # Puedes agregar model_config si quieres seguir el estilo de pydantic v2
    class config:
        orm_mode = True
    model_config = ConfigDict(from_attributes=True)