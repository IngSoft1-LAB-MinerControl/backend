from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, CheckConstraint , DateTime, Text, JSON, Date 
from sqlalchemy.orm import relationship
from src.database.database import Base
import datetime
import uuid

# Definición de los Modelos (Tablas)
class Game(Base):
    __tablename__ = 'games' 
    game_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30), nullable=False)
    status = Column(String(50), default='waiting players') # 'esperando jugadores', 'en curso', 'finalizada'
    max_players = Column(Integer, nullable=False)
    min_players = Column(Integer, nullable=False)
    players_amount = Column(Integer,nullable = False)
    current_turn = Column(Integer, nullable = True)
    cards_left = Column(Integer , nullable=True)
    players = relationship("Player", back_populates="game")
    cards = relationship("Card", back_populates="game")
    secrets = relationship("Secrets", back_populates="game")
    sets = relationship("Set" , back_populates="game")


class Player(Base):
    __tablename__ = 'players'
    player_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    host = Column(Boolean, default=False)
    birth_date = Column(Date, nullable = False)
    turn_order = Column(Integer) # Posición del jugador en el turno
    avatar = Column(String(255), nullable = True)
    game_id = Column(Integer, ForeignKey("games.game_id"), nullable=False)  
    game = relationship("Game", back_populates="players")
    cards = relationship("Card",primaryjoin="and_(Card.player_id == Player.player_id, Card.dropped == False)", back_populates="player")
    secrets = relationship("Secrets", back_populates="player")
    sets = relationship("Set" , back_populates="player")
    social_disgrace = Column(Boolean, default=False)  # Nueva columna para Social Disgrace

class Card(Base):
    __tablename__ = 'cards'
    card_id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(15))
    picked_up = Column(Boolean)
    dropped = Column(Boolean)
    player_id = Column(Integer, ForeignKey("players.player_id"), nullable=True)
    player = relationship("Player", back_populates="cards")
    game_id = Column(Integer, ForeignKey("games.game_id"), nullable=False)  
    game = relationship("Game", back_populates="cards")
    draft = Column(Boolean, default=False)
    discardInt = Column(Integer, default=0) # en caso de ser -1 representara que se jugo delay murderers escape

    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_abstract': True  
    }

class Detective(Card):
    __tablename__ ='detectives'
    name = Column(String(30))
    card_id = Column(Integer, ForeignKey('cards.card_id'), primary_key=True)
    quantity_set = Column(Integer)
    set_id = Column(Integer , ForeignKey("sets.set_id"), nullable=True)
    set = relationship("Set" , back_populates="detective")

    __mapper_args__ = {
        'polymorphic_identity': 'detective'
    }

class Event(Card):
    __tablename__ ='events'
    name = Column(String(30))
    card_id = Column(Integer, ForeignKey('cards.card_id'), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity': 'event'
    }

class Secrets(Base):
    __tablename__  = 'secrets'
    secret_id = Column(Integer, primary_key=True, autoincrement=True)
    murderer = Column(Boolean)
    acomplice = Column(Boolean)
    revelated = Column(Boolean)
    player_id = Column(Integer, ForeignKey("players.player_id"), nullable=True)  
    player = relationship("Player", back_populates="secrets")
    game_id = Column(Integer, ForeignKey("games.game_id"), nullable=False)  
    game = relationship("Game", back_populates="secrets")

    
class Set(Base):
    __tablename__ = 'sets'
    set_id = Column(Integer , primary_key=True , autoincrement=True)
    name = Column(String(30))
    player_id = Column(Integer, ForeignKey("players.player_id"), nullable=True)  
    player = relationship("Player", back_populates="sets")   
    game_id = Column(Integer, ForeignKey("games.game_id"), nullable=False)  
    game = relationship("Game", back_populates="sets")
    detective = relationship("Detective" , back_populates="set")


