from typing import List, Optional
from datetime import datetime

class Player:
    def __init__(self, name: str, role: str = "user"):
        self.name = name
        self.role = role  # "admin" или "user"
        self.score = 0

class Room:
    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: List[Player] = []
        self.state = "waiting"
        self.current_turn = 0
        self.prompt: Optional[str] = None
        self.image_url: Optional[str] = None
        self.empty_since: Optional[datetime] = None  # Когда комната опустела
        self.last_activity: datetime = datetime.utcnow()  # Когда была последняя активность

    def find_player(self, name: str) -> Optional[Player]:
        for player in self.players:
            if player.name == name:
                return player
        return None

    def add_player(self, name: str):
        role = "admin" if not self.players else "user"
        player = Player(name, role)
        self.players.append(player)
        self.empty_since = None  # Сбросить, когда зашел игрок
        self.update_activity()   # Обновить last_activity
        return player

    def remove_player(self, name: str):
        player = self.find_player(name)
        if player:
            self.players.remove(player)
            if len(self.players) == 0:
                self.empty_since = datetime.utcnow()  # Отметить, когда опустела
            self.update_activity()   # Обновить last_activity
            return player
        return None

    def get_player_names(self) -> List[str]:
        return [p.name for p in self.players]

    def set_prompt(self, prompt: str):
        self.prompt = prompt
        self.update_activity()   # Обновить last_activity

    def set_image_url(self, url: str):
        self.image_url = url
        self.update_activity()   # Обновить last_activity

    def next_turn(self):
        if not self.players:
            self.current_turn = 0
            return
        self.current_turn = (self.current_turn + 1) % len(self.players)
        self.update_activity()   # Обновить last_activity

    def add_score(self, player_name: str):
        player = self.find_player(player_name)
        if player:
            player.score += 1
            self.update_activity()   # Обновить last_activity

    def update_activity(self):
        """Обновляет время последней активности."""
        self.last_activity = datetime.utcnow()
