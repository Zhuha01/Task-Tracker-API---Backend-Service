from __future__ import annotations

from sqlalchemy import Enum, Text, cast, literal, null, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.models.enums import TaskStatus
from app.models.history import TaskStatusHistory
from app.models.task import Task
from app.schemas.activity import ActivityEventRead, ActivityEventType


def _coerce_task_status(value: object) -> TaskStatus | None:
    if value is None:
        return None
    if isinstance(value, TaskStatus):
        return value
    return TaskStatus(value)


async def get_project_activity(
    session: AsyncSession,
    project_id: int,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[ActivityEventRead]:
    status_enum = Enum(TaskStatus, native_enum=False)

    task_events = select(
        literal(ActivityEventType.task_created.value).label("event_type"),
        Task.id.label("source_id"),
        Task.created_at.label("created_at"),
        Task.author_id.label("actor_id"),
        Task.id.label("task_id"),
        Task.title.label("task_title"),
        cast(null(), status_enum).label("old_status"),
        cast(null(), status_enum).label("new_status"),
        cast(null(), Text).label("comment_text"),
    ).where(Task.project_id == project_id)

    status_events = (
        select(
            literal(ActivityEventType.task_status_changed.value).label("event_type"),
            TaskStatusHistory.id.label("source_id"),
            TaskStatusHistory.changed_at.label("created_at"),
            TaskStatusHistory.user_id.label("actor_id"),
            TaskStatusHistory.task_id.label("task_id"),
            Task.title.label("task_title"),
            TaskStatusHistory.old_status.label("old_status"),
            TaskStatusHistory.new_status.label("new_status"),
            cast(null(), Text).label("comment_text"),
        )
        .select_from(TaskStatusHistory)
        .join(Task, TaskStatusHistory.task_id == Task.id)
        .where(Task.project_id == project_id)
    )

    comment_events = (
        select(
            literal(ActivityEventType.comment_created.value).label("event_type"),
            Comment.id.label("source_id"),
            Comment.created_at.label("created_at"),
            Comment.user_id.label("actor_id"),
            Comment.task_id.label("task_id"),
            Task.title.label("task_title"),
            cast(null(), status_enum).label("old_status"),
            cast(null(), status_enum).label("new_status"),
            Comment.text.label("comment_text"),
        )
        .select_from(Comment)
        .join(Task, Comment.task_id == Task.id)
        .where(Task.project_id == project_id)
    )

    union_subq = union_all(task_events, status_events, comment_events).subquery()
    stmt = (
        select(union_subq)
        .order_by(union_subq.c.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.all()

    return [
        ActivityEventRead(
            event_type=ActivityEventType(row.event_type),
            created_at=row.created_at,
            actor_id=row.actor_id,
            task_id=row.task_id,
            task_title=row.task_title,
            source_id=row.source_id,
            old_status=_coerce_task_status(row.old_status),
            new_status=_coerce_task_status(row.new_status),
            comment_text=row.comment_text,
        )
        for row in rows
    ]
