from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.api.permissions import (
    check_admin,
    check_project_edit,
    check_project_member,
)
from app.crud.project import (
    add_member_to_project,
    create_project,
    delete_project,
    get_project,
    get_projects,
    remove_member_from_project,
    update_project,
)
from app.crud.user import get_user_by_id
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create(
    payload: ProjectCreate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    project = await create_project(session, payload, owner_id=current_user.id)
    created = await get_project(session, project.id)
    if created is None:
        raise HTTPException(status_code=500, detail="Failed to load project")
    return created


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    session: SessionDep,
    current_user: CurrentUserDep,
    all: bool = False,
):
    if all:
        check_admin(current_user)
        stmt = (
            select(Project).order_by(Project.id).options(selectinload(Project.members))
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    return await get_projects(session, current_user.id)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_by_id(
    project_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    project = await get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_member(current_user, project)
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def patch(
    project_id: int,
    payload: ProjectUpdate,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    project = await get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_edit(current_user, project)
    updated = await update_project(session, project, payload)
    return updated


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    project_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    project = await get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_edit(current_user, project)
    await delete_project(session, project)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{project_id}/members/{user_id}",
    response_model=ProjectRead,
    status_code=status.HTTP_200_OK,
)
async def add_member(
    project_id: int,
    user_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    project = await get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_edit(current_user, project)

    target_user = await get_user_by_id(session, user_id)
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    updated = await add_member_to_project(session, project, user_id=user_id)
    return updated


@router.delete(
    "/{project_id}/members/{user_id}",
    response_model=ProjectRead,
    status_code=status.HTTP_200_OK,
)
async def remove_member(
    project_id: int,
    user_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    project = await get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_edit(current_user, project)

    target_user = await get_user_by_id(session, user_id)
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    updated = await remove_member_from_project(session, project, user_id=user_id)
    return updated
