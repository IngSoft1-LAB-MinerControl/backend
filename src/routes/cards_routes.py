from fastapi import APIRouter, Depends, HTTPException  #te permite definir las rutas o subrutas por separado
from sqlalchemy.orm import Session  
from src.database.database import SessionLocal, get_db
from src.database.models import Card 

card = APIRouter()

@card.post("/cards/{game_id}")
def init_cards(game_id : int , db: Session = Depends(get_db)):
    i = 0
    while(i<61):
        new_card = Card(type = "Carta generica",
                    picked_up= False,
                    dropped= False,
                    player_id = None,
                    game_id= game_id)
        
        db.add(new_card)
        try:
            db.commit()
            db.refresh(new_card)
            i = i+1
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error creating card: {str(e)}")
    
    return None

@card.get("/lobby/cards/{game_id}")
def list_cards_ingame(game_id : int , db: Session = Depends(get_db)):
    cards = db.query(Card).filter(Card.game_id == game_id).all() # .all() me devuelve una lista, si no hay nada devuelve lista vacia
    if not cards:
        raise HTTPException(status_code=404, detail="No players found for the given game_id")
    return cards

