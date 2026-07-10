from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def get_notification(
    session: AsyncSession,
    notification_id: int,
) -> Optional[Notification]:
    stmt = select(Notification).where(Notification.id == notification_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_unread_for_user(
    session: AsyncSession,
    user_id: int,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_notification(
    session: AsyncSession,
    *,
    user_id: int,
    message: str,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        message=message,
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification


async def mark_as_read(
    session: AsyncSession,
    notification: Notification,
) -> Notification:
    notification.is_read = True
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification
