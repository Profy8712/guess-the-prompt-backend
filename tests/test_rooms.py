import pytest

@pytest.mark.asyncio
async def test_create_room(async_client):
    response = await async_client.post("/rooms")
    assert response.status_code == 200, f"Ошибка в /rooms: {response.text}"
    data = response.json()
    assert "room_id" in data
    assert len(data["room_id"]) > 0

@pytest.mark.asyncio
async def test_join_and_leave_room(async_client):
    response = await async_client.post("/rooms")
    room_id = response.json()["room_id"]

    join_resp = await async_client.post(f"/rooms/{room_id}/join", json={"player_name": "Player1"})
    assert join_resp.status_code == 200
    player = join_resp.json()
    assert player["name"] == "Player1"
    assert player["role"] == "admin"

    leave_resp = await async_client.post(f"/rooms/{room_id}/leave", json={"player_name": "Player1"})
    assert leave_resp.status_code == 200
    assert "left" in leave_resp.json()["message"]

@pytest.mark.asyncio
async def test_full_game_flow(async_client):
    prompt = "Cute panda eating bamboo"

    create_resp = await async_client.post("/rooms")
    room_id = create_resp.json()["room_id"]

    await async_client.post(f"/rooms/{room_id}/join", json={"player_name": "Alice"})
    await async_client.post(f"/rooms/{room_id}/join", json={"player_name": "Bob"})

    prompt_resp = await async_client.post(f"/rooms/{room_id}/prompt", json={
        "player_name": "Alice", "prompt": prompt
    })
    assert prompt_resp.status_code == 200
    assert "image_url" in prompt_resp.json()

    guess_resp = await async_client.post(f"/rooms/{room_id}/guess", json={
        "player_name": "Bob", "guess": prompt
    })
    assert guess_resp.status_code == 200
    data = guess_resp.json()
    assert data["correct"] is True
    assert data["score"] == 1

    next_resp = await async_client.post(f"/rooms/{room_id}/next")
    assert next_resp.status_code == 200
    assert "current_turn" in next_resp.json()
