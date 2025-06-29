from fastapi import APIRouter, HTTPException
from uuid import uuid4

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
from app.replicate_client import generate_image
from app.ws_manager import manager

rooms_storage = {}

rooms_router = APIRouter()

@rooms_router.post("/rooms", response_model=CreateRoomResponse)
async def create_room():
    if len(rooms_storage) >= 100:
        raise HTTPException(status_code=400, detail="Room limit reached (100 rooms)")
    room_id = str(uuid4())
    rooms_storage[room_id] = Room(room_id)
    return CreateRoomResponse(room_id=room_id)

@rooms_router.post("/rooms/{room_id}/join", response_model=PlayerInfo)
async def join_room(room_id: str, req: JoinRoomRequest):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if len(room.players) >= 10:
        raise HTTPException(status_code=400, detail="Room is full (max 10 players)")
    if room.find_player(req.player_name):
        raise HTTPException(status_code=400, detail="Player already in room")
    player = room.add_player(req.player_name)
    await manager.broadcast(room_id, {
        "event": "player_joined",
        "player": player.name,
        "players": room.get_player_names(),
    })
    return PlayerInfo(name=player.name, role=player.role, score=player.score)

@rooms_router.post("/rooms/{room_id}/leave")
async def leave_room(room_id: str, req: LeaveRoomRequest):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    player = room.remove_player(req.player_name)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found in room")
    await manager.broadcast(room_id, {
        "event": "player_left",
        "player": req.player_name,
        "players": room.get_player_names(),
    })
    if len(room.players) == 0:
        del rooms_storage[room_id]
        return {"message": f"Player {req.player_name} left and room {room_id} deleted"}
    if player.role == "admin" and room.players:
        room.players[0].role = "admin"
        await manager.broadcast(room_id, {
            "event": "admin_changed",
            "new_admin": room.players[0].name
        })
    return {"message": f"Player {req.player_name} left room {room_id}"}

@rooms_router.get("/rooms/{room_id}", response_model=RoomInfo)
async def get_room_info(room_id: str):
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

@rooms_router.post("/rooms/{room_id}/prompt")
async def submit_prompt(room_id: str, req: PromptRequest):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not room.players or room.players[room.current_turn].name != req.player_name:
        raise HTTPException(status_code=403, detail="Not your turn")
    # -- ДЛЯ DALL-E: Пропускаем проверку на длину промпта! --
    # if len(req.prompt.strip().split()) not in [1, 2]:
    #     raise HTTPException(status_code=400, detail="Prompt must be 1 or 2 words")
    room.set_prompt(req.prompt)
    try:
        image_url = await generate_image(req.prompt)
        room.set_image_url(image_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")
    await manager.broadcast(room_id, {
        "event": "new_round",
        "prompt": "[hidden]",  # скрываем prompt для игроков
        "image_url": room.image_url,
        "current_turn": room.current_turn,
        "players": room.get_player_names(),
    })
    return {"prompt": room.prompt, "image_url": room.image_url}

@rooms_router.post("/rooms/{room_id}/guess", response_model=ScoreUpdateResponse)
async def make_guess(room_id: str, req: GuessRequest):
    room = rooms_storage.get(room_id)
    if not room or not room.prompt:
        raise HTTPException(status_code=404, detail="No active round in this room")
    if req.player_name == room.players[room.current_turn].name:
        raise HTTPException(status_code=403, detail="You can't guess on your own prompt")
    correct = req.guess.strip().lower() == room.prompt.strip().lower()
    if correct:
        room.add_score(req.player_name)
        prev_turn = room.current_turn
        room.prompt = None
        room.image_url = None
        room.next_turn()
        await manager.broadcast(room_id, {
            "event": "correct_guess",
            "player": req.player_name,
            "score": room.find_player(req.player_name).score,
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
    return ScoreUpdateResponse(
        player_name=req.player_name,
        score=room.find_player(req.player_name).score,
        correct=correct,
    )

@rooms_router.post("/rooms/{room_id}/next")
async def next_turn(room_id: str):
    room = rooms_storage.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    prev_turn = room.current_turn
    room.next_turn()
    await manager.broadcast(room_id, {
        "event": "turn_changed",
        "prev_turn": prev_turn,
        "next_turn": room.current_turn,
    })
    return {"current_turn": room.current_turn}
