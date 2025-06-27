from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.rooms import rooms_router
from app.db.rooms_db import rooms_db_router
from app.ws_manager import manager

app = FastAPI(title="Guess the Prompt Backend")

# --- CORS (Dev: allow all, Prod: specify your domains) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use a specific list in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------------------------------------

# Routers
app.include_router(rooms_router)
app.include_router(rooms_db_router)

@app.get("/")
def root():
    return {"message": "Guess the Prompt backend is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.websocket("/ws/rooms/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(room_id, {"event": "chat", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(room_id, {"event": "left", "message": "A player left the room"})
