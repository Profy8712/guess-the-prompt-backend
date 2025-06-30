import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_register_and_login(async_client: AsyncClient):
    res = await async_client.post("/accounts/register", json={"username": "test", "password": "1234"})
    assert res.status_code == 200

    res = await async_client.post("/accounts/login", json={"username": "test", "password": "1234"})
    assert res.status_code == 200
    assert "access_token" in res.json()