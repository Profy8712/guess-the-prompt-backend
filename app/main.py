import os
import random
import string
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from app.rooms import rooms_router, rooms_storage
from app.db.rooms_db import rooms_db_router
from app.accounts.routes import accounts_router
from app.accounts.auth import decode_access_token
from app.ws_manager import manager
from app.replicate_client import generate_image

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in the environment!")

app = FastAPI(title="Guess the Prompt Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(rooms_router)
app.include_router(rooms_db_router)
app.include_router(accounts_router, prefix="/api/v1/accounts", tags=["Accounts"])

@app.get("/")
def root():
    return {"message": "Guess the Prompt backend is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.websocket("/ws/rooms/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    token = websocket.query_params.get("token")
    if not token:
        username = "Guest_" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        role = "guest"
    else:
        try:
            payload = decode_access_token(token)
            if not payload:
                raise Exception("Invalid token")
            username = payload.get("sub")
            role = payload.get("role", "user")
            if not username:
                raise Exception("No username in token")
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await manager.connect(room_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            if event == "prompt":
                if role != "admin":
                    await manager.send_personal_message(
                        websocket,
                        {"event": "error", "message": "Only admin can set the prompt."}
                    )
                    continue

                prompt = data.get("prompt", "").strip()
                if not prompt or len(prompt.split()) > 2:
                    await manager.send_personal_message(
                        websocket,
                        {"event": "error", "message": "Prompt must be 1–2 words only."}
                    )
                    continue

                try:
                    image_url = await generate_image(prompt)
                    await manager.broadcast(room_id, {
                        "event": "image_generated",
                        "image_url": image_url
                    })
                except Exception as e:
                    await manager.send_personal_message(
                        websocket,
                        {"event": "error", "message": f"Image generation failed: {str(e)}"}
                    )

            elif event == "chat":
                await manager.broadcast(room_id, {
                    "event": "chat",
                    "data": data.get("data"),
                    "from": username
                })

            elif event == "get_room_state":
                room = rooms_storage.get(room_id)
                if room:
                    from app.schemas import RoomInfo, PlayerInfo
                    players = [
                        PlayerInfo(name=p.name, role=p.role, score=p.score)
                        for p in room.players
                    ]
                    await manager.send_personal_message(
                        websocket,
                        RoomInfo(
                            room_id=room.room_id,
                            players=players,
                            state=room.state,
                            current_turn=room.current_turn,
                            prompt=room.prompt,
                            image_url=room.image_url,
                            current_admin=room.get_admin() if hasattr(room, "get_admin") else None,
                            current_prompter=room.players[room.current_turn].name if room.players else None
                        ).dict()
                    )

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(room_id, {
            "event": "left",
            "message": f"{username} left the room"
        })
