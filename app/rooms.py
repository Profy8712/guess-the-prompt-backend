from fastapi import APIRouter, HTTPException
from uuid import uuid4
from app.schemas import (
    CreateRoomResponse, JoinRoomRequest, PlayerInfo, RoomInfo, LeaveRoomRequest
)
from app.models import Room

rooms_storage = {}

rooms_router = APIRouter()

@rooms_router.post("/rooms", response_model=CreateRoomResponse)
def create_room():
    if len(rooms_storage) >= 100:
        raise HTTPException(status_code=400, detail="Room limit reached (100 rooms)")
    room_id = str(uuid4())
    rooms_storage[room_id] = Room(room_id)
    return CreateRoomResponse(room_id=room_id)

@rooms_router.post("/rooms/{room_id}/join", response_model=PlayerInfo)
def join_room(room_id: str, req: JoinRoomRequest):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if len(room.players) >= 10:
        raise HTTPException(status_code=400, detail="Room is full (max 10 players)")
    if room.find_player(req.player_name):
        raise HTTPException(status_code=400, detail="Player already in room")
    player = room.add_player(req.player_name)
    return PlayerInfo(name=player.name, role=player.role, score=player.score)

@rooms_router.post("/rooms/{room_id}/leave")
def leave_room(room_id: str, req: LeaveRoomRequest):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    player = room.remove_player(req.player_name)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found in room")
    if len(room.players) == 0:
        del rooms_storage[room_id]
        return {"message": f"Player {req.player_name} left and room {room_id} deleted"}
    if player.role == "admin" and room.players:
        room.players[0].role = "admin"
    return {"message": f"Player {req.player_name} left room {room_id}"}

@rooms_router.get("/rooms/{room_id}", response_model=RoomInfo)
def get_room_info(room_id: str):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
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
    )
