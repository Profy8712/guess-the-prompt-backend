from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(room_id, []).append(websocket)

    def disconnect(self, room_id: str, websocket: WebSocket):
        if room_id in self.active_connections:
            try:
                self.active_connections[room_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception:
            # Клиент, вероятно, уже отключился
            pass

    async def broadcast(self, room_id: str, message: dict):
        # Отправляем всем, удаляем отвалившиеся соединения
        for ws in self.active_connections.get(room_id, [])[:]:  # делаем копию списка!
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(room_id, ws)

manager = ConnectionManager()
