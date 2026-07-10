from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.models.enums import Role
from app.models.user import User


async def test_create_list_get_update_delete_project(
    client: AsyncClient,
    user_token_headers: dict[str, str],
):
    create = await client.post(
        "/api/v1/projects",
        headers=user_token_headers,
        json={"name": "Alpha", "description": "First project"},
    )
    assert create.status_code == 201
    project_id = create.json()["id"]
    assert create.json()["name"] == "Alpha"

    listed = await client.get("/api/v1/projects", headers=user_token_headers)
    assert listed.status_code == 200
    assert any(p["id"] == project_id for p in listed.json())

    fetched = await client.get(
        f"/api/v1/projects/{project_id}",
        headers=user_token_headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["description"] == "First project"

    patched = await client.patch(
        f"/api/v1/projects/{project_id}",
        headers=user_token_headers,
        json={"name": "Alpha Renamed"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Alpha Renamed"

    deleted = await client.delete(
        f"/api/v1/projects/{project_id}",
        headers=user_token_headers,
    )
    assert deleted.status_code == 204


async def test_add_and_remove_project_member(
    client: AsyncClient,
    db_session: AsyncSession,
    test_project,
    user_token_headers: dict[str, str],
):
    member = User(
        email="invitee@example.com",
        name="Invitee",
        hashed_password=get_password_hash("testpass123"),
        role=Role.user,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)

    added = await client.post(
        f"/api/v1/projects/{test_project.id}/members/{member.id}",
        headers=user_token_headers,
    )
    assert added.status_code == 200
    member_ids = [m["id"] for m in added.json()["members"]]
    assert member.id in member_ids

    member_headers = {
        "Authorization": f"Bearer {create_access_token(subject=member.email)}"
    }
    as_member = await client.get(
        f"/api/v1/projects/{test_project.id}",
        headers=member_headers,
    )
    assert as_member.status_code == 200

    removed = await client.delete(
        f"/api/v1/projects/{test_project.id}/members/{member.id}",
        headers=user_token_headers,
    )
    assert removed.status_code == 200
    member_ids = [m["id"] for m in removed.json()["members"]]
    assert member.id not in member_ids
