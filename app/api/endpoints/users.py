from __future__ import annotations

from typing import Annotated, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.crud.user import (
    delete_user,
    get_user_by_email,
    get_user_by_id,
    get_users,
    update_user,
)
from app.db.session import get_db
from app.models.enums import Role
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]
CurrentAdminDep = Annotated[User, Depends(get_current_admin)]


@router.get("", response_model=Union[list[UserRead], UserRead])
async def list_users_or_get_user(
    session: SessionDep,
    current_admin: CurrentAdminDep,
    user_id: Optional[int] = None,
):
    _ = current_admin
    if user_id is None:
        return await get_users(session)

    user = await get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUserDep):
    return current_user


@router.patch("/me", response_model=UserRead)
async def patch_me(
    payload: UserUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    if payload.role is not None:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    if payload.email is not None:
        existing_user = await get_user_by_email(session, payload.email)
        if existing_user is not None and existing_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="User already exists")

    updated = await update_user(
        session,
        user=current_user,
        user_in=payload,
        allow_role_change=False,
    )
    return updated


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    session: SessionDep,
    current_user: CurrentUserDep,
):
    await delete_user(session, user=current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_by_id(
    user_id: int,
    session: SessionDep,
    current_admin: CurrentAdminDep,
):
    target_user = await get_user_by_id(session, user_id)
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.role == Role.admin and target_user.id != current_admin.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    await delete_user(session, user=target_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{user_id}", response_model=UserRead)
async def patch_user(
    user_id: int,
    payload: UserUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    target_user = await get_user_by_id(session, user_id)
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    is_self = current_user.id == user_id
    is_admin = current_user.role == Role.admin

    if not is_self and not is_admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    if is_admin and not is_self and target_user.role == Role.admin:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    if not is_admin and payload.role is not None:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    if payload.email is not None:
        existing_user = await get_user_by_email(session, payload.email)
        if existing_user is not None and existing_user.id != target_user.id:
            raise HTTPException(status_code=400, detail="User already exists")

    allow_role_change = is_admin and not is_self and target_user.role != Role.admin
    updated = await update_user(
        session,
        user=target_user,
        user_in=payload,
        allow_role_change=allow_role_change,
    )
    return updated
