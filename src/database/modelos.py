from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, CheckConstraint , DateTime, Text, JSON
from sqlalchemy.orm import relationship
from .database import Base
import datetime
import uuid

# Definición de los Modelos (Tablas)
class Partida(Base):
    __tablename__ = 'partidas' 
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(15), unique=True, nullable=False)
    estado = Column(String(50), default='esperando jugadores') # 'esperando jugadores', 'en curso', 'finalizada'
    max_jugadores = Column(Integer, nullable=False)
    min_jugadores = Column(Integer, nullable=False)
    __table_args__ = (
        CheckConstraint('max_jugadores >= 2 AND max_jugadores <= 6', name='max_jugadores_check'),
        CheckConstraint('min_jugadores >= 2 AND min_jugadores <= 6', name='min_jugadores_check'),
    )

class Jugador(Base):
    __tablename__ = 'jugadores'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    es_anfitrion = Column(Boolean, default=False)
    partida_id = Column(String(36), ForeignKey("partidas.id"), nullable=False)  
    partida = relationship("Partida", back_populates="jugadores")
