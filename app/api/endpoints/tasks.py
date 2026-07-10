from __future__ import annotations

from typing import Annotated, List, Literal, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.permissions import (
    check_assignee_is_project_member,
    check_project_member,
    check_task_access,
)
from app.core.cache import (
    cache_get_json,
    cache_set_json,
    task_list_cache_key,
)
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.core.ws import ws_manager
from app.crud.project import get_project
from app.crud.task import (
    create_task,
    delete_task,
    get_task,
    get_tasks,
    search_tasks,
    update_task,
    update_task_status,
)
from app.crud.user import get_user_by_email
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

    cache_key = task_list_cache_key(
        project_id,
        status=status.value if status else None,
        priority=priority.value if priority else None,
        assignee_id=assignee_id,
        sort_by=sort_by,
        skip=skip,
        limit=limit,
    )
    cached = await cache_get_json(cache_key)
    if cached is not None:
        return cached

    tasks = await get_tasks(
        session,
        project_id,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        sort_by=sort_by,
        skip=skip,
        limit=limit,
    )
    payload = [TaskRead.model_validate(task).model_dump(mode="json") for task in tasks]
    await cache_set_json(cache_key, payload)
    return tasks


@router.get("/projects/{project_id}/tasks/search", response_model=List[TaskRead])
async def search_project_tasks(
    project_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
    q: Annotated[str, Query(min_length=1)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    project = await get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_member(current_user, project)

    return await search_tasks(session, project_id, q, skip=skip, limit=limit)


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

    updated = await update_task_status(
        session,
        task,
        payload,
        actor_id=current_user.id,
    )
    await ws_manager.broadcast(
        updated.project_id,
        {
            "event": "task_status_changed",
            "task_id": updated.id,
            "project_id": updated.project_id,
            "status": updated.status.value,
            "changed_by": current_user.id,
        },
    )
    return updated


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


@router.websocket("/projects/{project_id}/ws")
async def project_task_status_ws(
    websocket: WebSocket,
    project_id: int,
    token: Annotated[str, Query(...)],
    session: SessionDep,
):
    """Live task status updates for a project. Auth via `?token=<access_jwt>`."""
    try:
        payload = decode_token(token)
        if payload.get("type") != TOKEN_TYPE_ACCESS:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        email = payload.get("sub")
        if not email:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        user = await get_user_by_email(session, email)
        if user is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        project = await get_project(session, project_id)
        if project is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        check_project_member(user, project)
    except (JWTError, HTTPException):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await ws_manager.connect(project_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(project_id, websocket)
