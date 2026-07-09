from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.enums import Role
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_users(session: AsyncSession) -> list[User]:
    stmt = select(User).order_by(User.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_user(session: AsyncSession, user_in: UserCreate) -> User:
    count_stmt = select(func.count(User.id))
    count_result = await session.execute(count_stmt)
    users_count = count_result.scalar_one()
    role = Role.admin if users_count == 0 else Role.user

    user = User(
        email=str(user_in.email),
        name=user_in.name,
        hashed_password=get_password_hash(user_in.password),
        role=role,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(
    session: AsyncSession,
    obj: User,
    obj_in: UserUpdate,
) -> User:
    update_data = obj_in.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    if "email" in update_data:
        update_data["email"] = str(update_data["email"])
    for field, value in update_data.items():
        setattr(obj, field, value)

    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def delete_user(session: AsyncSession, *, user: User) -> None:
    await session.delete(user)
    await session.commit()
