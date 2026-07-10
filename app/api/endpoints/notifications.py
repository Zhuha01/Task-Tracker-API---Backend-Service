from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.permissions import check_notification_access
from app.crud.notification import (
    get_notification,
    get_unread_for_user,
    mark_as_read,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.notification import NotificationRead

router = APIRouter(tags=["Notifications"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.get("/notifications/unread", response_model=List[NotificationRead])
async def list_unread(
    session: SessionDep,
    current_user: CurrentUserDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    return await get_unread_for_user(
        session,
        current_user.id,
        skip=skip,
        limit=limit,
    )


@router.patch("/notifications/{notification_id}/read", response_model=NotificationRead)
async def mark_notification_read(
    notification_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    notification = await get_notification(session, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    check_notification_access(current_user, notification)

    return await mark_as_read(session, notification)
