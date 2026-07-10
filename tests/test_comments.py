from __future__ import annotations

from httpx import AsyncClient

from app.models.task import Task
from app.models.user import User


async def test_comment_crud_and_author_only_edit(
    client: AsyncClient,
    test_task: Task,
    user_token_headers: dict[str, str],
    member_user: User,
    member_token_headers: dict[str, str],
):
    created = await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_token_headers,
        json={"text": "Owner comment"},
    )
    assert created.status_code == 201
    comment_id = created.json()["id"]
    assert created.json()["text"] == "Owner comment"

    listed = await client.get(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=member_token_headers,
    )
    assert listed.status_code == 200
    assert any(c["id"] == comment_id for c in listed.json())

    forbidden = await client.patch(
        f"/api/v1/comments/{comment_id}",
        headers=member_token_headers,
        json={"text": "Hijacked"},
    )
    assert forbidden.status_code == 403

    updated = await client.patch(
        f"/api/v1/comments/{comment_id}",
        headers=user_token_headers,
        json={"text": "Edited by author"},
    )
    assert updated.status_code == 200
    assert updated.json()["text"] == "Edited by author"

    delete_forbidden = await client.delete(
        f"/api/v1/comments/{comment_id}",
        headers=member_token_headers,
    )
    assert delete_forbidden.status_code == 403

    deleted = await client.delete(
        f"/api/v1/comments/{comment_id}",
        headers=user_token_headers,
    )
    assert deleted.status_code == 204
