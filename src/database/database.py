from sqlalchemy import create_engine, true
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = "mysql+pymysql://lucaMaccioni:minercontrol@localhost:3306/agathaJuego_db"
engine = create_engine(DATABASE_URL, pool_size = 11, max_overflow = 20)



Base = declarative_base()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  


Base.metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)