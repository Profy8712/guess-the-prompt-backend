from pydantic import BaseModel
from typing import List, Optional

class CreateRoomResponse(BaseModel):
    room_id: str

class JoinRoomRequest(BaseModel):
    player_name: str

class PlayerInfo(BaseModel):
    name: str
    role: str
    score: int

class RoomInfo(BaseModel):
    room_id: str
    players: List[PlayerInfo]
    state: str
    current_turn: int
    prompt: Optional[str] = None
    image_url: Optional[str] = None

class LeaveRoomRequest(BaseModel):
    player_name: str
