from pydantic import BaseModel, ConfigDict, Field
from typing import Literal, Optional, Union, Annotated 

class Card_Response(BaseModel): 
    card_id : int
    player_id : Optional[int] = None
    game_id : int
    picked_up : bool
    dropped : bool
    draft: bool
    discardInt: int
    class config:
        orm_mode = True
    model_config = ConfigDict(from_attributes=True)    

class Detective_Response(Card_Response): 
    type : Literal ['detective'] = 'detective'
    name : str
    quantity_set : int
    set_id : Optional[int] = None
    class config:
        orm_mode = True
    model_config = ConfigDict(from_attributes=True) 
      

class Event_Response(Card_Response): 
    type : Literal ['event']  = 'event'
    name : str
    class config:
        orm_mode = True
    model_config = ConfigDict(from_attributes=True)
      

AllCardsResponse = Annotated [
    Union[Detective_Response, Event_Response],
    Field(discriminator = 'type')]


   
class Discard_List_Request(BaseModel):
    #Esquema para recibir una lista de IDs de cartas a descartar
    card_ids: list[int]

    # Puedes agregar model_config si quieres seguir el estilo de pydantic v2
    class config:
        orm_mode = True
    model_config = ConfigDict(from_attributes=True)
