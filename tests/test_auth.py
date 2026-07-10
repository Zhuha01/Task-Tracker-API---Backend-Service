from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import TEST_PASSWORD


async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers


async def test_register_login_me_and_refresh(client: AsyncClient, test_user):
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "name": "New User",
            "password": "password123",
        },
    )
    assert register.status_code == 201
    assert register.json()["email"] == "newuser@example.com"
    assert register.json()["role"] == "user"

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "newuser@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["token_type"] == "bearer"
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    me = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "newuser@example.com"

    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh.status_code == 200
    assert "access_token" in refresh.json()

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204


async def test_login_rejects_bad_password(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": test_user.email, "password": "wrong-password"},
    )
    assert response.status_code == 401


async def test_register_duplicate_email(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user.email,
            "name": "Duplicate",
            "password": TEST_PASSWORD,
        },
    )
    assert response.status_code == 400
