import pytest

@pytest.mark.asyncio
async def test_profile_and_leaderboard(async_client):
    # Зарегистрируем и залогиним пользователя
    res = await async_client.post("/api/v1/accounts/register", json={"username": "tester", "password": "pass123"})
    assert res.status_code == 200
    res = await async_client.post("/api/v1/accounts/login", json={"username": "tester", "password": "pass123"})
    token = res.json()["access_token"]

    # Получаем профиль по токену
    res = await async_client.get(
        "/api/v1/accounts/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "tester"
    assert "total_score" in data

    # Лидерборд (с одним пользователем)
    res = await async_client.get("/api/v1/accounts/leaderboard")
    assert res.status_code == 200
    assert any(u["username"] == "tester" for u in res.json())
