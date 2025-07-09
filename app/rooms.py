from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
from datetime import datetime
import asyncio
import random

from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import (
    CreateRoomResponse,
    JoinRoomRequest,
    PlayerInfo,
    RoomInfo,
    LeaveRoomRequest,
    PromptRequest,
    GuessRequest,
    ScoreUpdateResponse,
)
from app.models import Room
from app.db.database import get_db
from app.db.models_db import User
from app.replicate_client import generate_image
from app.ws_manager import manager

rooms_storage = {}

rooms_router = APIRouter()

# --- Cleaning of rooms ---
ROOM_CLEANUP_PERIOD_SECONDS = 60
ROOM_EMPTY_DELETE_SECONDS = 15 * 60
ROOM_INACTIVE_DELETE_SECONDS = 30 * 60

cleanup_task_started = False

async def cleanup_rooms():
    while True:
        now = datetime.utcnow()
        to_delete = []
        for room_id, room in list(rooms_storage.items()):
            if room.empty_since:
                age = (now - room.empty_since).total_seconds()
                if age > ROOM_EMPTY_DELETE_SECONDS:
                    to_delete.append(room_id)
                    continue
            if hasattr(room, "last_activity") and room.last_activity:
                inactivity = (now - room.last_activity).total_seconds()
                if inactivity > ROOM_INACTIVE_DELETE_SECONDS:
                    to_delete.append(room_id)
        for room_id in set(to_delete):
            del rooms_storage[room_id]
            print(f"[RoomCleanup] Room {room_id} auto-deleted (empty or inactive)")
        await asyncio.sleep(ROOM_CLEANUP_PERIOD_SECONDS)

def ensure_cleanup_task(loop=None):
    global cleanup_task_started
    if not cleanup_task_started:
        loop = loop or asyncio.get_event_loop()
        loop.create_task(cleanup_rooms())
        cleanup_task_started = True

@rooms_router.on_event("startup")
async def on_startup():
    ensure_cleanup_task()

def mark_activity(room):
    room.last_activity = datetime.utcnow()

async def broadcast_room_update(room_id, room):
    players = [
        PlayerInfo(name=p.name, role=p.role, score=p.score)
        for p in room.players
    ]
    await manager.broadcast(room_id, {
        "event": "room_update",
        "data": RoomInfo(
            room_id=room.room_id,
            players=players,
            state=room.state,
            current_turn=room.current_turn,
            prompt=room.prompt,
            image_url=room.image_url,
            current_admin=room.get_admin() if hasattr(room, "get_admin") else None,
            current_prompter=room.players[room.current_turn].name if room.players else None
        ).dict()
    })

@rooms_router.post("/rooms", response_model=CreateRoomResponse)
async def create_room():
    ensure_cleanup_task()
    if len(rooms_storage) >= 100:
        raise HTTPException(status_code=400, detail="Room limit reached (100 rooms)")
    room_id = str(uuid4())
    new_room = Room(room_id)
    new_room.last_activity = datetime.utcnow()
    rooms_storage[room_id] = new_room
    await broadcast_room_update(room_id, new_room)
    return CreateRoomResponse(room_id=room_id)

@rooms_router.post("/rooms/{room_id}/join", response_model=PlayerInfo)
async def join_room(room_id: str, req: JoinRoomRequest, db: AsyncSession = Depends(get_db)):
    ensure_cleanup_task()
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if len(room.players) >= 10:
        raise HTTPException(status_code=400, detail="Room is full (max 10 players)")
    # --- ВАЖНО: не допускаем дублирования ---
    player = room.find_player(req.player_name)
    if player is not None:
        raise HTTPException(status_code=400, detail="Player already in room")
    # Найти user_id по имени, если есть такой User
    result = await db.execute(
        User.__table__.select().where(User.username == req.player_name)
    )
    user = result.first()
    user_id = user.id if user else None
    # В add_player дубли теперь невозможны
    player = room.add_player(req.player_name, user_id=user_id)
    if player is None:
        raise HTTPException(status_code=400, detail="Player already in room")
    mark_activity(room)
    await manager.broadcast(room_id, {
        "event": "player_joined",
        "player": player.name,
        "players": room.get_player_names(),
    })
    await broadcast_room_update(room_id, room)
    return PlayerInfo(name=player.name, role=player.role, score=player.score)

@rooms_router.post("/rooms/{room_id}/leave")
async def leave_room(room_id: str, req: LeaveRoomRequest):
    ensure_cleanup_task()
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    player = room.remove_player(req.player_name)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found in room")
    mark_activity(room)
    await manager.broadcast(room_id, {
        "event": "player_left",
        "player": req.player_name,
        "players": room.get_player_names(),
    })
    if len(room.players) == 0:
        await broadcast_room_update(room_id, room)
        return {"message": f"Player {req.player_name} left; room {room_id} will be auto-deleted after 15 min if empty"}
    if player.role == "admin" and room.players:
        new_admin = random.choice(room.players)
        for p in room.players:
            p.role = "user"
        new_admin.role = "admin"
        await manager.broadcast(room_id, {
            "event": "admin_changed",
            "new_admin": new_admin.name
        })
    await broadcast_room_update(room_id, room)
    return {"message": f"Player {req.player_name} left room {room_id}"}

@rooms_router.get("/rooms/{room_id}", response_model=RoomInfo)
async def get_room_info(room_id: str):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    mark_activity(room)
    players = [
        PlayerInfo(name=p.name, role=p.role, score=p.score)
        for p in room.players
    ]
    return RoomInfo(
        room_id=room.room_id,
        players=players,
        state=room.state,
        current_turn=room.current_turn,
        prompt=room.prompt,
        image_url=room.image_url,
        current_admin=room.get_admin() if hasattr(room, "get_admin") else None,
        current_prompter=room.players[room.current_turn].name if room.players else None
    )

@rooms_router.post("/rooms/{room_id}/prompt")
async def submit_prompt(room_id: str, req: PromptRequest):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not room.players or room.players[room.current_turn].name != req.player_name:
        raise HTTPException(status_code=403, detail="Not your turn")
    room.set_prompt(req.prompt)
    mark_activity(room)
    try:
        image_url = await generate_image(req.prompt)
        room.set_image_url(image_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {e}")
    await manager.broadcast(room_id, {
        "event": "new_round",
        "prompt": "[hidden]",
        "image_url": room.image_url,
        "current_turn": room.current_turn,
        "players": room.get_player_names(),
    })
    await broadcast_room_update(room_id, room)
    return {"prompt": room.prompt, "image_url": room.image_url}

@rooms_router.post("/rooms/{room_id}/guess", response_model=ScoreUpdateResponse)
async def make_guess(room_id: str, req: GuessRequest, db: AsyncSession = Depends(get_db)):
    room = rooms_storage.get(room_id)
    if not room or not room.prompt:
        raise HTTPException(status_code=404, detail="No active round in this room")
    if req.player_name == room.players[room.current_turn].name:
        raise HTTPException(status_code=403, detail="You can't guess on your own prompt")
    correct = req.guess.strip().lower() == room.prompt.strip().lower()
    mark_activity(room)
    player = room.find_player(req.player_name)
    if correct:
        room.add_score(req.player_name)
        # Update User in DB
        if player and player.user_id:
            user = await db.get(User, player.user_id)
            if user:
                user.total_score += 1
                user.total_games += 1
                await db.commit()
        prev_turn = room.current_turn
        room.prompt = None
        room.image_url = None
        room.next_turn()
        await manager.broadcast(room_id, {
            "event": "correct_guess",
            "player": req.player_name,
            "score": player.score if player else 0,
            "answer": req.guess,
            "prev_turn": prev_turn,
            "next_turn": room.current_turn,
        })
    else:
        await manager.broadcast(room_id, {
            "event": "wrong_guess",
            "player": req.player_name,
            "guess": req.guess,
        })
    await broadcast_room_update(room_id, room)
    return ScoreUpdateResponse(
        player_name=req.player_name,
        score=player.score if player else 0,
        correct=correct,
    )

@rooms_router.post("/rooms/{room_id}/next")
async def next_turn(room_id: str):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    prev_turn = room.current_turn
    room.next_turn()
    mark_activity(room)
    await manager.broadcast(room_id, {
        "event": "turn_changed",
        "prev_turn": prev_turn,
        "next_turn": room.current_turn,
    })
    await broadcast_room_update(room_id, room)
    return {"current_turn": room.current_turn}
