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
from app.db.database import get_db
from app.db.models_db import User
from app.replicate_client import generate_image
from app.ws_manager import manager
from typing import List, Optional

class Player:
    def __init__(self, name: str, role: str = "user", user_id: Optional[int] = None):
        self.name = name
        self.role = role
        self.score = 0
        self.user_id = user_id
        self.prompt_submitted = False
        self.guessed = False

class Room:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: List[Player] = []
        self.state = "waiting"
        self.current_turn = 0
        self.round_number = 1
        self.round_count = 5
        self.prompt_words = 1
        self.turn_length = 60
        self.prompt: Optional[str] = None
        self.image_url: Optional[str] = None
        self.empty_since: Optional[datetime] = None
        self.last_activity: datetime = datetime.utcnow()
        self.timer_task: Optional[asyncio.Task] = None

    def find_player(self, name: str) -> Optional[Player]:
        for player in self.players:
            if player.name == name:
                return player
        return None

    def add_player(self, name: str, user_id: Optional[int] = None):
        if self.find_player(name):
            return None
        role = "admin" if not self.players else "user"
        player = Player(name, role, user_id)
        self.players.append(player)
        self.empty_since = None
        self.update_activity()
        return player

    def remove_player(self, name: str):
        player = self.find_player(name)
        if player:
            self.players.remove(player)
            if len(self.players) == 0:
                self.empty_since = datetime.utcnow()
            self.update_activity()
            return player
        return None

    def get_player_names(self) -> List[str]:
        return [p.name for p in self.players]

    def set_prompt(self, prompt: str):
        self.prompt = prompt
        self.update_activity()

    def set_image_url(self, url: str):
        self.image_url = url
        self.update_activity()

    def next_turn(self):
        if not self.players:
            self.current_turn = 0
            return
        self.current_turn = (self.current_turn + 1) % len(self.players)
        self.update_activity()

    def add_score(self, player_name: str):
        player = self.find_player(player_name)
        if player:
            player.score += 1
            self.update_activity()

    def update_activity(self):
        self.last_activity = datetime.utcnow()

    def get_admin(self) -> Optional[str]:
        for p in self.players:
            if p.role == "admin":
                return p.name
        return None

    def to_settings(self):
        return {
            "round_count": self.round_count,
            "prompt_words": self.prompt_words,
            "turn_length": self.turn_length,
        }

    def reset_guesses(self):
        for idx, p in enumerate(self.players):
            p.guessed = (idx == self.current_turn)

    def all_have_guessed(self):
        for idx, p in enumerate(self.players):
            if idx == self.current_turn:
                continue
            if not getattr(p, "guessed", False):
                return False
        return True

    def reset_game(self):
        self.state = "waiting"
        self.current_turn = 0
        self.round_number = 1
        self.prompt = None
        self.image_url = None
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
        self.timer_task = None
        for p in self.players:
            p.score = 0
            p.prompt_submitted = False
            p.guessed = False

rooms_storage = {}
rooms_router = APIRouter()

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
            current_admin=room.get_admin(),
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
    if room.find_player(req.player_name):
        raise HTTPException(status_code=400, detail="Player already in room")
    result = await db.execute(
        User.__table__.select().where(User.username == req.player_name)
    )
    user = result.first()
    user_id = user.id if user else None
    player = room.add_player(req.player_name, user_id=user_id)
    if player is None:
        raise HTTPException(status_code=400, detail="Cannot add player")
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
        current_admin=room.get_admin(),
        current_prompter=room.players[room.current_turn].name if room.players else None
    )

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

@rooms_router.post("/rooms/{room_id}/start_game", response_model=StartGameResponse)
async def start_game(room_id: str):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.state != "waiting":
        raise HTTPException(status_code=400, detail="Game already started")
    room.state = "playing"
    room.round_number = 1
    room.current_turn = 0  # Start from the first player
    for player in room.players:
        player.score = 0
        player.prompt_submitted = False
        player.guessed = False
    if room.timer_task and not room.timer_task.done():
        room.timer_task.cancel()
    room.timer_task = None
    await manager.broadcast(room_id, {
        "event": "game_started",
        "settings": room.to_settings(),
        "players": [p.name for p in room.players],
        "current_turn": room.current_turn,
        "current_prompter": room.players[room.current_turn].name if room.players else None,
    })
    await broadcast_room_update(room_id, room)
    # Wait for the first prompt before starting timer
    return StartGameResponse(
        message="Game started",
        settings=room.to_settings(),
    )

@rooms_router.post("/rooms/{room_id}/restart_game")
async def restart_game(room_id: str):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room.reset_game()
    await manager.broadcast(room_id, {
        "event": "game_restarted"
    })
    await broadcast_room_update(room_id, room)
    return {"message": "Game restarted"}

async def start_turn_with_timer(room_id: str):
    room = rooms_storage.get(room_id)
    if not room or room.state != "playing":
        return
    room.reset_guesses()
    await manager.broadcast(room_id, {
        "event": "turn_started",
        "current_turn": room.current_turn,
        "turn_length": room.turn_length,
        "round_number": room.round_number,
        "current_prompter": room.players[room.current_turn].name if room.players else None,
    })
    await countdown(room_id, room.turn_length)

async def countdown(room_id: str, seconds: int):
    room = rooms_storage.get(room_id)
    for remaining in range(seconds, 0, -1):
        if remaining % 5 == 0 or remaining <= 5:
            await manager.broadcast(room_id, {
                "event": "timer_update",
                "seconds_left": remaining,
            })
        await asyncio.sleep(1)
        if room.timer_task and room.timer_task.cancelled():
            return
    await end_turn(room_id)

async def end_turn(room_id: str):
    room = rooms_storage.get(room_id)
    if not room or room.state != "playing":
        return
    prev_turn = room.current_turn

    # Сброс prompt и image_url
    room.prompt = None
    room.image_url = None

    room.next_turn()
    # Завершить игру если все раунды сыграны
    if room.current_turn == 0:
        room.round_number += 1
        if room.round_number > room.round_count:
            room.state = "finished"
            if room.timer_task and not room.timer_task.done():
                room.timer_task.cancel()
            await manager.broadcast(room_id, {
                "event": "game_finished",
                "scores": {p.name: p.score for p in room.players},
            })
            return
    if room.timer_task and not room.timer_task.done():
        room.timer_task.cancel()
    room.timer_task = None
    # Сообщаем фронту кто теперь prompter
    await manager.broadcast(room_id, {
        "event": "turn_time_expired",
        "current_turn": prev_turn,
        "next_turn": room.current_turn,
        "current_prompter": room.players[room.current_turn].name if room.players else None,
    })
    await manager.broadcast(room_id, {
        "event": "await_prompt",
        "current_turn": room.current_turn,
        "current_prompter": room.players[room.current_turn].name if room.players else None,
    })
    await broadcast_room_update(room_id, room)

@rooms_router.post("/rooms/{room_id}/prompt")
async def submit_prompt(room_id: str, req: PromptRequest):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not room.players or room.players[room.current_turn].name != req.player_name:
        raise HTTPException(status_code=403, detail="Not your turn")
    if room.prompt:
        raise HTTPException(status_code=400, detail="Prompt already submitted for this turn")
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
        "current_prompter": room.players[room.current_turn].name if room.players else None,
    })
    await broadcast_room_update(room_id, room)
    if room.timer_task and not room.timer_task.done():
        room.timer_task.cancel()
    room.timer_task = asyncio.create_task(start_turn_with_timer(room_id))
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
    player.guessed = True

    if correct:
        room.add_score(req.player_name)
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
            "current_prompter": room.players[room.current_turn].name if room.players else None,
        })
        if room.timer_task and not room.timer_task.done():
            room.timer_task.cancel()
        room.timer_task = None
        await manager.broadcast(room_id, {
            "event": "await_prompt",
            "current_turn": room.current_turn,
            "current_prompter": room.players[room.current_turn].name if room.players else None,
        })
    else:
        await manager.broadcast(room_id, {
            "event": "wrong_guess",
            "player": req.player_name,
            "guess": req.guess,
        })
    await broadcast_room_update(room_id, room)
    if room.all_have_guessed():
        if room.timer_task and not room.timer_task.done():
            room.timer_task.cancel()
        await end_turn(room_id)
    return ScoreUpdateResponse(
        player_name=req.player_name,
        score=player.score if player else 0,
        correct=correct,
    )
