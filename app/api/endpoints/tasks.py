from __future__ import annotations

from typing import Annotated, List, Literal, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.permissions import (
    check_assignee_is_project_member,
    check_project_member,
    check_task_access,
)
from app.crud.project import get_project
from app.crud.task import (
    create_task,
    delete_task,
    get_task,
    get_tasks,
    update_task,
    update_task_status,
)
from app.db.session import get_db
from app.models.enums import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.task import TaskCreate, TaskRead, TaskStatusUpdate, TaskUpdate

router = APIRouter(tags=["Tasks"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.get("/projects/{project_id}/tasks", response_model=List[TaskRead])
async def list_tasks(
    project_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    assignee_id: Optional[int] = None,
    sort_by: Literal["created_at", "deadline", "priority"] = "created_at",
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    project = await get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_member(current_user, project)

    return await get_tasks(
        session,
        project_id,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        sort_by=sort_by,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    project_id: int,
    payload: TaskCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
):
    project = await get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_member(current_user, project)
    check_assignee_is_project_member(project, payload.assignee_id)

    return await create_task(
        session,
        project_id=project_id,
        author_id=current_user.id,
        task_in=payload,
        background_tasks=background_tasks,
    )


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def get_by_id(
    task_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    task = await get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    check_task_access(current_user, task)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def patch(
    task_id: int,
    payload: TaskUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
):
    task = await get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    check_task_access(current_user, task)

    if "assignee_id" in payload.model_dump(exclude_unset=True):
        check_assignee_is_project_member(task.project, payload.assignee_id)

    return await update_task(
        session,
        task,
        payload,
        actor_id=current_user.id,
        background_tasks=background_tasks,
    )


@router.patch("/tasks/{task_id}/status", response_model=TaskRead)
async def patch_status(
    task_id: int,
    payload: TaskStatusUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    task = await get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    check_task_access(current_user, task)

    return await update_task_status(
        session,
        task,
        payload,
        actor_id=current_user.id,
    )


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    task_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    task = await get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    check_task_access(current_user, task)

    await delete_task(session, task)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
