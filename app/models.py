from typing import List, Optional
from datetime import datetime

class Player:
    def __init__(self, name: str, role: str = "user", user_id: Optional[int] = None):
        self.name = name
        self.role = role  # "admin" or "user"
        self.score = 0
        self.user_id = user_id

class Room:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: List[Player] = []
        self.state = "waiting"
        self.current_turn = 0
        self.prompt: Optional[str] = None
        self.image_url: Optional[str] = None
        self.empty_since: Optional[datetime] = None
        self.last_activity: datetime = datetime.utcnow()

    def find_player(self, name: str) -> Optional[Player]:
        for player in self.players:
            if player.name == name:
                return player
        return None

    def add_player(self, name: str, user_id: Optional[int] = None):
        # Prevent duplicates!
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
