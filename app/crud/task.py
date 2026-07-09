from __future__ import annotations

from typing import Literal, Optional

from sqlalchemy import Select, case, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import TaskPriority, TaskStatus
from app.models.history import TaskStatusHistory
from app.models.project import Project
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate

SortBy = Literal["created_at", "deadline", "priority"]


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
    return task


async def update_task(
    session: AsyncSession,
    task: Task,
    task_in: TaskUpdate,
) -> Task:
    if task_in.title is not None:
        task.title = task_in.title
    if task_in.description is not None:
        task.description = task_in.description
    if task_in.priority is not None:
        task.priority = task_in.priority
    if task_in.deadline is not None:
        task.deadline = task_in.deadline
    if "assignee_id" in task_in.model_fields_set:
        task.assignee_id = task_in.assignee_id

    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def update_task_status(
    session: AsyncSession,
    task_id: int,
    new_status: TaskStatus,
    user_id: int,
) -> Optional[Task]:
    stmt = select(Task).where(Task.id == task_id)
    result = await session.execute(stmt)
    task = result.scalar_one_or_none()
    if task is None:
        return None

    old_status = task.status
    if old_status != new_status:
        task.status = new_status
        history = TaskStatusHistory(
            task_id=task.id,
            user_id=user_id,
            old_status=old_status,
            new_status=new_status,
        )
        session.add(history)

    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def delete_task(session: AsyncSession, task: Task) -> None:
    await session.delete(task)
    await session.commit()
