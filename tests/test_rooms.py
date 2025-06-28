import pytest

from app.schemas import (
    CreateRoomResponse,
    PlayerInfo,
    RoomInfo,
    ScoreUpdateResponse,
)

async def test_create_room(client):
    response = await client.post("/rooms")
    assert response.status_code == 200
    data = response.json()
    assert "room_id" in data
    assert len(data["room_id"]) > 0

async def test_join_and_leave_room(client):
    # Создаём комнату
    response = await client.post("/rooms")
    room_id = response.json()["room_id"]

    # Присоединяемся как игрок
    join_resp = await client.post(f"/rooms/{room_id}/join", json={"player_name": "Player1"})
    assert join_resp.status_code == 200
    player = join_resp.json()
    assert player["name"] == "Player1"
    assert player["role"] == "admin"
    assert player["score"] == 0

    # Получаем инфу о комнате
    info_resp = await client.get(f"/rooms/{room_id}")
    assert info_resp.status_code == 200
    room_info = info_resp.json()
    assert room_info["room_id"] == room_id
    assert len(room_info["players"]) == 1
    assert room_info["players"][0]["name"] == "Player1"

    # Игрок выходит
    leave_resp = await client.post(f"/rooms/{room_id}/leave", json={"player_name": "Player1"})
    assert leave_resp.status_code == 200
    assert "left" in leave_resp.json()["message"]

async def test_full_game_flow(client):
    # Создаём комнату
    create_resp = await client.post("/rooms")
    room_id = create_resp.json()["room_id"]

    # Два игрока присоединяются
    await client.post(f"/rooms/{room_id}/join", json={"player_name": "Alice"})
    await client.post(f"/rooms/{room_id}/join", json={"player_name": "Bob"})

    # Alice задаёт промпт
    prompt = "cat"
    prompt_resp = await client.post(f"/rooms/{room_id}/prompt", json={"player_name": "Alice", "prompt": prompt})
    assert prompt_resp.status_code == 200
    assert "image_url" in prompt_resp.json()

    # Bob угадывает правильно
    guess_resp = await client.post(f"/rooms/{room_id}/guess", json={"player_name": "Bob", "guess": prompt})
    assert guess_resp.status_code == 200
    score_update = guess_resp.json()
    assert score_update["player_name"] == "Bob"
    assert score_update["score"] == 1
    assert score_update["correct"] is True

    # Пробуем неправильный ответ (теперь ход Bob, а Alice угадывает неверно)
    await client.post(f"/rooms/{room_id}/prompt", json={"player_name": "Bob", "prompt": "dog"})
    wrong_guess = await client.post(f"/rooms/{room_id}/guess", json={"player_name": "Alice", "guess": "elephant"})
    assert wrong_guess.status_code == 200
    assert wrong_guess.json()["correct"] is False

    # Принудительный переход хода
    next_turn = await client.post(f"/rooms/{room_id}/next")
    assert next_turn.status_code == 200
    assert "current_turn" in next_turn.json()
