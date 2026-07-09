from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.permissions import check_comment_author, check_task_access
from app.crud.comment import (
    create_comment,
    delete_comment,
    get_comment,
    get_task_comments,
    update_comment,
)
from app.crud.task import get_task
from app.db.session import get_db
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentRead, CommentUpdate

router = APIRouter(tags=["Comments"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.get("/tasks/{task_id}/comments", response_model=List[CommentRead])
async def list_comments(
    task_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    task = await get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    check_task_access(current_user, task)

    return await get_task_comments(session, task_id, skip=skip, limit=limit)


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    task_id: int,
    payload: CommentCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    task = await get_task(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    check_task_access(current_user, task)

    return await create_comment(
        session,
        task_id=task_id,
        author_id=current_user.id,
        comment_in=payload,
    )


@router.patch("/comments/{comment_id}", response_model=CommentRead)
async def patch(
    comment_id: int,
    payload: CommentUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    comment = await get_comment(session, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    check_comment_author(current_user, comment)

    return await update_comment(session, comment, payload)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    comment_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    comment = await get_comment(session, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    check_comment_author(current_user, comment)

    await delete_comment(session, comment)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
