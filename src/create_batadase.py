from database.database import Base, engine
from database.models import  Player, Game


Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("Tablas recreadas correctamente")
