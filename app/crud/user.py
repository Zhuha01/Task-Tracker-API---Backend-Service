from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user_in: UserCreate) -> User:
    user = User(
        email=str(user_in.email),
        name=user_in.name,
        hashed_password=get_password_hash(user_in.password),
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
