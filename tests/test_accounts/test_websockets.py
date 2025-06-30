# tests/test_accounts/test_websockets.py

from starlette.testclient import TestClient
from app.main import app
from app.accounts.auth import create_access_token

def get_token(username="test", role="user"):
    return create_access_token({"sub": username, "role": role})

def test_websocket_chat_broadcast():
    client = TestClient(app)
    token1 = get_token("alice")
    token2 = get_token("bob")

    with client.websocket_connect(f"/ws/rooms/testroom?token={token1}") as ws1, \
         client.websocket_connect(f"/ws/rooms/testroom?token={token2}") as ws2:

        # Alice sends a chat message
        ws1.send_json({"event": "chat", "data": "Hello from Alice!"})

        # Bob receives the chat message
        message = ws2.receive_json()
        assert message["event"] == "chat"
        assert message["data"] == "Hello from Alice!"
        assert message["from"] == "alice"

def test_websocket_prompt_only_admin():
    client = TestClient(app)
    token_user = get_token("bob", "user")
    token_admin = get_token("alice", "admin")

    # Ordinary user tries to send a prompt (should receive an error)
    with client.websocket_connect(f"/ws/rooms/testroom2?token={token_user}") as ws:
        ws.send_json({"event": "prompt", "prompt": "cat"})
        data = ws.receive_json()
        assert data["event"] == "error"
        assert "Only admin can set the prompt" in data["message"]

    # Admin sends a prompt (should receive image_generated or error if mock fails)
    with client.websocket_connect(f"/ws/rooms/testroom2?token={token_admin}") as ws:
        ws.send_json({"event": "prompt", "prompt": "dog"})
        # Если у тебя мокнут generate_image — должен прилететь "image_generated"
        data = ws.receive_json()
        # Можно так:
        # assert data["event"] == "image_generated" or data["event"] == "error"

def test_websocket_invalid_token():
    client = TestClient(app)
    bad_token = "invalid.jwt.token"
    # При невалидном токене FastAPI обычно закрывает соединение с 1008 (POLICY_VIOLATION)
    from starlette.websockets import WebSocketDisconnect

    try:
        with client.websocket_connect(f"/ws/rooms/room99?token={bad_token}") as ws:
            ws.send_json({"event": "chat", "data": "hacker!"})
    except WebSocketDisconnect as e:
        # e.code == 1008 most likely; FastAPI/Starlette throws this on bad auth
        assert e.code == 1008
    else:
        assert False, "WebSocket connection should have been closed due to invalid token"
