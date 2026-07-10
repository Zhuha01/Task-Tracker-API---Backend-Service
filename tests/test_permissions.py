from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.models.enums import Role
from app.models.user import User


@pytest.fixture
async def non_member_user(db_session: AsyncSession) -> User:
    user = User(
        email="stranger@example.com",
        name="Non Member",
        hashed_password=get_password_hash("testpass123"),
        role=Role.user,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def non_member_token_headers(non_member_user: User) -> dict[str, str]:
    token = create_access_token(subject=non_member_user.email)
    return {"Authorization": f"Bearer {token}"}


async def test_non_member_cannot_list_project_tasks(
    client: AsyncClient,
    test_project,
    non_member_token_headers: dict[str, str],
):
    response = await client.get(
        f"/api/v1/projects/{test_project.id}/tasks",
        headers=non_member_token_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"


async def test_admin_can_list_project_tasks(
    client: AsyncClient,
    test_project,
    admin_token_headers: dict[str, str],
):
    response = await client.get(
        f"/api/v1/projects/{test_project.id}/tasks",
        headers=admin_token_headers,
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_project_owner_can_list_project_tasks(
    client: AsyncClient,
    test_project,
    user_token_headers: dict[str, str],
):
    response = await client.get(
        f"/api/v1/projects/{test_project.id}/tasks",
        headers=user_token_headers,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
