from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.notification import create_notification
from app.models.user import User


async def test_list_unread_and_mark_read(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    user_token_headers: dict[str, str],
    member_user: User,
    member_token_headers: dict[str, str],
):
    notification = await create_notification(
        db_session,
        user_id=test_user.id,
        message="You were assigned",
    )

    unread = await client.get(
        "/api/v1/notifications/unread",
        headers=user_token_headers,
    )
    assert unread.status_code == 200
    ids = [n["id"] for n in unread.json()]
    assert notification.id in ids

    foreign = await client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers=member_token_headers,
    )
    assert foreign.status_code == 403

    marked = await client.patch(
        f"/api/v1/notifications/{notification.id}/read",
        headers=user_token_headers,
    )
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    unread_after = await client.get(
        "/api/v1/notifications/unread",
        headers=user_token_headers,
    )
    assert notification.id not in [n["id"] for n in unread_after.json()]
