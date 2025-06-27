from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.rooms import rooms_router
from app.ws_manager import manager

app = FastAPI(title="Guess the Prompt Backend")

app.include_router(rooms_router)

@app.get("/")
def root():
    return {"message": "Guess the Prompt backend is running"}

@app.websocket("/ws/rooms/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Simple echo for test, you can expand this for custom events
            await manager.broadcast(room_id, {"event": "chat", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(room_id, {"event": "left", "message": "A player left the room"})
