from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


DATABASE_URL = "postgresql://angelo_user:MinerControl@localhost:5432/mi_juego_db"

engine = create_engine(DATABASE_URL)
Base = declarative_base() # Base para tus modelos declarativos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Creación de las Tablas en la Base de Datos
# Esto crea las tablas definidas por tus modelos si no existen.
# ¡Úsalo con precaución en producción o asegúrate de tener migraciones!
Base.metadata.create_all(engine)

# Crear una Sesión para Interactuar con la DB
Session = sessionmaker(bind=engine)