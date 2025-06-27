from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String, unique=True, index=True)
    state = Column(String, default="waiting")
    current_turn = Column(Integer, default=0)

    players = relationship("Player", back_populates="room", cascade="all, delete-orphan")

class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    role = Column(String)
    score = Column(Integer, default=0)
    room_id = Column(Integer, ForeignKey("rooms.id"))

    room = relationship("Room", back_populates="players")
