
import pytest

@pytest.mark.asyncio
async def test_create_room(client):
    response = await client.post("/rooms")
    assert response.status_code == 200, f"Ошибка в /rooms: {response.text}"
    data = response.json()
    assert "room_id" in data
    assert len(data["room_id"]) > 0


@pytest.mark.asyncio
async def test_join_and_leave_room(client):
    response = await client.post("/rooms")
    assert response.status_code == 200, f"Ошибка в /rooms: {response.text}"
    room_id = response.json()["room_id"]

    join_resp = await client.post(f"/rooms/{room_id}/join", json={"player_name": "Player1"})
    assert join_resp.status_code == 200, f"Ошибка в /join: {join_resp.text}"
    player = join_resp.json()
    assert player["name"] == "Player1"
    assert player["role"] == "admin"
    assert player["score"] == 0

    info_resp = await client.get(f"/rooms/{room_id}")
    assert info_resp.status_code == 200, f"Ошибка в GET /rooms/{room_id}: {info_resp.text}"
    room_info = info_resp.json()
    assert room_info["room_id"] == room_id
    assert len(room_info["players"]) == 1
    assert room_info["players"][0]["name"] == "Player1"

    leave_resp = await client.post(f"/rooms/{room_id}/leave", json={"player_name": "Player1"})
    assert leave_resp.status_code == 200, f"Ошибка в /leave: {leave_resp.text}"
    assert "left" in leave_resp.json()["message"]


@pytest.mark.asyncio
async def test_full_game_flow(client):
    prompt = "A cute cat playing with a ball of yarn, watercolor illustration"

    create_resp = await client.post("/rooms")
    assert create_resp.status_code == 200, f"Ошибка при создании комнаты: {create_resp.text}"
    room_id = create_resp.json()["room_id"]

    join_resp1 = await client.post(f"/rooms/{room_id}/join", json={"player_name": "Alice"})
    assert join_resp1.status_code == 200, f"Ошибка при подключении Alice: {join_resp1.text}"

    join_resp2 = await client.post(f"/rooms/{room_id}/join", json={"player_name": "Bob"})
    assert join_resp2.status_code == 200, f"Ошибка при подключении Bob: {join_resp2.text}"

    # Alice задаёт промпт
    prompt_resp = await client.post(
        f"/rooms/{room_id}/prompt",
        json={"player_name": "Alice", "prompt": prompt},
    )
    assert prompt_resp.status_code == 200, f"Ошибка prompt: {prompt_resp.text}"
    assert "image_url" in prompt_resp.json()

    # Bob угадывает правильно
    guess_resp = await client.post(
        f"/rooms/{room_id}/guess",
        json={"player_name": "Bob", "guess": prompt},
    )
    assert guess_resp.status_code == 200, f"Ошибка guess (Bob): {guess_resp.text}"
    score_update = guess_resp.json()
    assert score_update["player_name"] == "Bob"
    assert score_update["score"] == 1
    assert score_update["correct"] is True

    # Bob задаёт свой промпт
    prompt2 = await client.post(
        f"/rooms/{room_id}/prompt",
        json={"player_name": "Bob", "prompt": "A happy dog on the beach, digital art"},
    )
    assert prompt2.status_code == 200, f"Ошибка prompt2 (Bob): {prompt2.text}"

    # Alice ошибается
    wrong_guess = await client.post(
        f"/rooms/{room_id}/guess",
        json={"player_name": "Alice", "guess": "elephant"},
    )
    assert wrong_guess.status_code == 200, f"Ошибка wrong_guess (Alice): {wrong_guess.text}"
    assert wrong_guess.json()["correct"] is False

    # Завершаем раунд
    next_turn = await client.post(f"/rooms/{room_id}/next")
    assert next_turn.status_code == 200, f"Ошибка next_turn: {next_turn.text}"
    assert "current_turn" in next_turn.json()
