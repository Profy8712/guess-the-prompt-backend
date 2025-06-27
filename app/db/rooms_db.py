from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import uuid4

from app.db.database import get_db
from app.db.models_db import Room

rooms_db_router = APIRouter()

@rooms_db_router.post("/rooms/create_db")
async def create_room_db(db: AsyncSession = Depends(get_db)):
    # Генерируем уникальный room_id
    room_id = str(uuid4())
    room = Room(room_id=room_id, state="waiting", current_turn=0)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return {"id": room.id, "room_id": room.room_id}

@rooms_db_router.get("/rooms/all_db")
async def get_all_rooms_db(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room))
    rooms = result.scalars().all()
    return [
        {
            "id": room.id,
            "room_id": room.room_id,
            "state": room.state,
            "current_turn": room.current_turn,
        }
        for room in rooms
    ]
