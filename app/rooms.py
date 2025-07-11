from fastapi import APIRouter, HTTPException, Depends
from uuid import uuid4
from datetime import datetime
import asyncio
import random

from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import (
    CreateRoomResponse, JoinRoomRequest, PlayerInfo, RoomInfo,
    LeaveRoomRequest, PromptRequest, GuessRequest, ScoreUpdateResponse,
    ChangeSettingsRequest, KickPlayerRequest, StartGameResponse,
)
from app.models import Room
from app.db.database import get_db
from app.db.models_db import User
from app.replicate_client import generate_image
from app.ws_manager import manager

rooms_storage = {}

rooms_router = APIRouter()

# --- Room cleanup ---
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

# ---- CREATE, JOIN, LEAVE, INFO (без изменений) ----
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
    if room.find_player(req.player_name):
        raise HTTPException(status_code=400, detail="Player already in room")
    # user_id если есть
    result = await db.execute(
        User.__table__.select().where(User.username == req.player_name)
    )
    user = result.first()
    user_id = user.id if user else None
    player = room.add_player(req.player_name, user_id=user_id)
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

# ---- CHANGE SETTINGS ----
@rooms_router.post("/rooms/{room_id}/change_settings")
async def change_settings(room_id: str, req: ChangeSettingsRequest):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room.round_count = req.round_count
    room.prompt_words = req.prompt_words
    room.turn_length = req.turn_length
    await broadcast_room_update(room_id, room)
    return {"message": "Settings updated", "settings": room.to_settings()}

# ---- KICK PLAYER ----
@rooms_router.post("/rooms/{room_id}/kick_player")
async def kick_player(room_id: str, req: KickPlayerRequest):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    player = room.find_player(req.player_name)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    room.remove_player(req.player_name)
    await manager.broadcast(room_id, {
        "event": "player_kicked",
        "player": req.player_name,
    })
    await broadcast_room_update(room_id, room)
    return {"message": f"Player {req.player_name} was kicked."}

# ---- START GAME ----
@rooms_router.post("/rooms/{room_id}/start_game", response_model=StartGameResponse)
async def start_game(room_id: str):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.state != "waiting":
        raise HTTPException(status_code=400, detail="Game already started")
    room.state = "playing"
    room.round_number = 1
    for player in room.players:
        player.score = 0
        player.prompt_submitted = False
    await manager.broadcast(room_id, {
        "event": "game_started",
        "settings": room.to_settings(),
        "players": [p.name for p in room.players],
    })
    asyncio.create_task(start_turn_with_timer(room_id))
    return StartGameResponse(
        message="Game started",
        settings=room.to_settings(),
    )

# ====== Таймер и обработка ходов ======
async def start_turn_with_timer(room_id: str):
    room = rooms_storage.get(room_id)
    if not room or room.state != "playing":
        return
    await manager.broadcast(room_id, {
        "event": "turn_started",
        "current_turn": room.current_turn,
        "turn_length": room.turn_length,
        "round_number": room.round_number,
    })
    await countdown(room_id, room.turn_length)

async def countdown(room_id: str, seconds: int):
    for remaining in range(seconds, 0, -5):
        await manager.broadcast(room_id, {
            "event": "timer_update",
            "seconds_left": remaining,
        })
        await asyncio.sleep(5 if remaining > 5 else remaining)
    await end_turn(room_id)

async def end_turn(room_id: str):
    room = rooms_storage.get(room_id)
    if not room or room.state != "playing":
        return
    await manager.broadcast(room_id, {
        "event": "turn_time_expired",
        "current_turn": room.current_turn,
    })
    room.next_turn()
    if room.current_turn == 0:
        room.round_number += 1
        if room.round_number > room.round_count:
            room.state = "finished"
            await manager.broadcast(room_id, {
                "event": "game_finished",
                "scores": {p.name: p.score for p in room.players},
            })
            return
    asyncio.create_task(start_turn_with_timer(room_id))
