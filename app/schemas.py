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
    current_admin: Optional[str] = None
    current_prompter: Optional[str] = None

class LeaveRoomRequest(BaseModel):
    player_name: str

class PromptRequest(BaseModel):
    player_name: str
    prompt: str

class GuessRequest(BaseModel):
    player_name: str
    guess: str

class ScoreUpdateResponse(BaseModel):
    player_name: str
    score: int
    correct: bool
