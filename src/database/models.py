from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, CheckConstraint , DateTime, Text, JSON, Date 
from sqlalchemy.orm import relationship
from src.database.database import Base
import datetime
import uuid

# Definición de los Modelos (Tablas)
class Game(Base):
    __tablename__ = 'games' 
    game_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(15), nullable=False)
    status = Column(String(50), default='esperando jugadores') # 'esperando jugadores', 'en curso', 'finalizada'
    max_players = Column(Integer, nullable=False)
    min_players = Column(Integer, nullable=False)
    players = relationship("Player", back_populates="game")

class Player(Base):
    __tablename__ = 'players'
    player_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    host = Column(Boolean, default=False)
    birth_date = Column(Date, nullable = False)
    game_id = Column(Integer, ForeignKey("games.game_id"), nullable=False)  
    game = relationship("Game", back_populates="players")

class Card(Base):
    __tablename__ = 'cards'
    card_id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(15))
    picked_up = Column(Boolean)
    dropped = Column(Boolean)
    player_id = Column(Integer, ForeignKey("players.player_id"), nullable=False)  
    player = relationship("Players", back_populates="cards")

class Secrets(Base):
    __tablename__ = 'Secrets'
    secret_id = Column(Integer, primary_key=True, autoincrement=True)
    murderer = Column(Boolean)
    acomplice = Column(Boolean)
    revelated = Column(Boolean)
    player_id = Column(Integer, ForeignKey("players.player_id"), nullable=False)  
    player = relationship("Players", back_populates="players")

    
   


