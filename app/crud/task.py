from __future__ import annotations

from typing import Literal, Optional

from fastapi import BackgroundTasks
from sqlalchemy import Select, case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.notification import create_notification
from app.crud.user import get_user_by_id
from app.models.enums import TaskPriority, TaskStatus
from app.models.history import TaskStatusHistory
from app.models.project import Project
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskStatusUpdate, TaskUpdate
from app.services.notifications import mock_send_email

SortBy = Literal["created_at", "deadline", "priority"]


async def _notify_assignee(
    session: AsyncSession,
    background_tasks: BackgroundTasks,
    *,
    assignee_id: int,
    message: str,
) -> None:
    await create_notification(session, user_id=assignee_id, message=message)
    assignee = await get_user_by_id(session, assignee_id)
    if assignee:
        background_tasks.add_task(mock_send_email, assignee.email, message)


def _apply_task_filters(
    stmt: Select[tuple[Task]],
    *,
    status: Optional[TaskStatus],
    priority: Optional[TaskPriority],
    assignee_id: Optional[int],
) -> Select[tuple[Task]]:
    if status is not None:
        stmt = stmt.where(Task.status == status)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if assignee_id is not None:
        stmt = stmt.where(Task.assignee_id == assignee_id)
    return stmt


def _apply_task_sort(stmt: Select[tuple[Task]], sort_by: SortBy) -> Select[tuple[Task]]:
    if sort_by == "created_at":
        return stmt.order_by(Task.created_at.desc())
    if sort_by == "deadline":
        return stmt.order_by(Task.deadline.asc().nullslast())
    priority_order = case(
        (Task.priority == TaskPriority.high, 3),
        (Task.priority == TaskPriority.medium, 2),
        (Task.priority == TaskPriority.low, 1),
        else_=0,
    )
    return stmt.order_by(priority_order.desc())


async def get_task(session: AsyncSession, task_id: int) -> Optional[Task]:
    stmt = (
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.project).selectinload(Project.members),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_tasks(
    session: AsyncSession,
    project_id: int,
    *,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    assignee_id: Optional[int] = None,
    sort_by: SortBy = "created_at",
    skip: int = 0,
    limit: int = 100,
) -> list[Task]:
    stmt = select(Task).where(Task.project_id == project_id)
    stmt = _apply_task_filters(
        stmt,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
    )
    stmt = _apply_task_sort(stmt, sort_by)
    stmt = stmt.offset(skip).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_task(
    session: AsyncSession,
    *,
    project_id: int,
    author_id: int,
    task_in: TaskCreate,
    background_tasks: BackgroundTasks,
) -> Task:
    task = Task(
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority,
        deadline=task_in.deadline,
        project_id=project_id,
        author_id=author_id,
        assignee_id=task_in.assignee_id,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)

    if task_in.assignee_id is not None and task_in.assignee_id != author_id:
        await _notify_assignee(
            session,
            background_tasks,
            assignee_id=task_in.assignee_id,
            message=f'You have been assigned to task "{task.title}"',
        )

    return task


async def update_task(
    session: AsyncSession,
    obj: Task,
    obj_in: TaskUpdate,
    *,
    actor_id: int,
    background_tasks: BackgroundTasks,
) -> Task:
    update_data = obj_in.model_dump(exclude_unset=True)
    old_assignee_id = obj.assignee_id
    for field, value in update_data.items():
        setattr(obj, field, value)

    session.add(obj)
    await session.commit()
    await session.refresh(obj)

    if (
        "assignee_id" in update_data
        and obj.assignee_id is not None
        and obj.assignee_id != old_assignee_id
        and obj.assignee_id != actor_id
    ):
        await _notify_assignee(
            session,
            background_tasks,
            assignee_id=obj.assignee_id,
            message=f'You have been assigned to task "{obj.title}"',
        )

    return obj


async def update_task_status(
    session: AsyncSession,
    obj: Task,
    obj_in: TaskStatusUpdate,
    *,
    actor_id: int,
) -> Task:
    update_data = obj_in.model_dump(exclude_unset=True)
    old_status = obj.status
    for field, value in update_data.items():
        setattr(obj, field, value)

    if "status" in update_data and update_data["status"] != old_status:
        history = TaskStatusHistory(
            task_id=obj.id,
            user_id=actor_id,
            old_status=old_status,
            new_status=update_data["status"],
        )
        session.add(history)

    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def delete_task(session: AsyncSession, task: Task) -> None:
    await session.delete(task)
    await session.commit()
