from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.comment import Comment
from app.models.project import Project
from app.models.task import Task
from app.schemas.comment import CommentCreate, CommentUpdate


async def get_comment(session: AsyncSession, comment_id: int) -> Optional[Comment]:
    stmt = (
        select(Comment)
        .where(Comment.id == comment_id)
        .options(
            selectinload(Comment.task)
            .selectinload(Task.project)
            .selectinload(Project.members),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_task_comments(
    session: AsyncSession,
    task_id: int,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Comment]:
    stmt = (
        select(Comment)
        .where(Comment.task_id == task_id)
        .order_by(Comment.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_comment(
    session: AsyncSession,
    *,
    task_id: int,
    author_id: int,
    comment_in: CommentCreate,
) -> Comment:
    comment = Comment(
        task_id=task_id,
        user_id=author_id,
        text=comment_in.text,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return comment


async def update_comment(
    session: AsyncSession,
    obj: Comment,
    obj_in: CommentUpdate,
) -> Comment:
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(obj, field, value)

    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def delete_comment(session: AsyncSession, comment: Comment) -> None:
    await session.delete(comment)
    await session.commit()
