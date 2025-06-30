import os
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.rooms import rooms_router
from app.db.rooms_db import rooms_db_router
from app.ws_manager import manager
from app.replicate_client import generate_image  # Генерация изображений через Replicate

# Загрузка переменных из .env
load_dotenv()

# Проверка SECRET_KEY
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in the environment!")

app = FastAPI(title="Guess the Prompt Backend")

# --- CORS (Dev: allow all, Prod: specify your domains) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Указать домены в проде!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------------------------------------

# Routers
app.include_router(rooms_router)
app.include_router(rooms_db_router)
# Будущие роутеры, например:
# app.include_router(auth_router)

# Healthcheck
@app.get("/")
def root():
    return {"message": "Guess the Prompt backend is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

# --- WebSocket для комнаты ---
@app.websocket("/ws/rooms/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await manager.connect(room_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            if event == "prompt":
                prompt = data.get("prompt", "").strip()

                # Проверка промпта
                if not prompt or len(prompt.split()) > 2:
                    await manager.send_personal_message(
                        {"event": "error", "message": "Prompt must be 1–2 words only."},
                        websocket
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
                        {"event": "error", "message": f"Image generation failed: {str(e)}"},
                        websocket
                    )

            elif event == "chat":
                await manager.broadcast(room_id, {
                    "event": "chat",
                    "data": data.get("data")
                })

    except WebSocketDisconnect:
        manager.disconnect(room_id, websocket)
        await manager.broadcast(room_id, {
            "event": "left",
            "message": "A player left the room"
        })
