from __future__ import annotations

from httpx import AsyncClient


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
