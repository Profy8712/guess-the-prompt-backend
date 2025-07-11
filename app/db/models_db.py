from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    total_games = Column(Integer, default=0)
    total_score = Column(Integer, default=0)
    avatar_url = Column(String, nullable=True)

    players = relationship("Player", back_populates="user", cascade="all, delete-orphan")

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, unique=True, index=True)
    state = Column(String, default="waiting")
    current_turn = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    players = relationship("Player", back_populates="room", cascade="all, delete-orphan")

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    role = Column(String)
    score = Column(Integer, default=0)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    room = relationship("Room", back_populates="players")
    user = relationship("User", back_populates="players")
