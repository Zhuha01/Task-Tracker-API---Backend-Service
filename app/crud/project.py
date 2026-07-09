from __future__ import annotations

from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.user import get_user_by_id
from app.models.project import Project, project_members
from app.schemas.project import ProjectCreate, ProjectUpdate


async def create_project(
    session: AsyncSession,
    project_in: ProjectCreate,
    owner_id: int,
) -> Project:
    project = Project(
        name=project_in.name,
        description=project_in.description,
        owner_id=owner_id,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def get_project(session: AsyncSession, project_id: int) -> Optional[Project]:
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.members))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_projects(session: AsyncSession, user_id: int) -> list[Project]:
    stmt = (
        select(Project)
        .outerjoin(project_members, Project.id == project_members.c.project_id)
        .where(or_(Project.owner_id == user_id, project_members.c.user_id == user_id))
        .distinct()
        .order_by(Project.id)
        .options(selectinload(Project.members))
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_project(
    session: AsyncSession,
    project: Project,
    project_update: ProjectUpdate,
) -> Project:
    if project_update.name is not None:
        project.name = project_update.name
    if project_update.description is not None:
        project.description = project_update.description

    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def delete_project(session: AsyncSession, project: Project) -> None:
    await session.delete(project)
    await session.commit()


async def add_member_to_project(
    session: AsyncSession,
    project: Project,
    user_id: int,
) -> Project:
    user = await get_user_by_id(session, user_id)
    if user is None:
        return project

    if any(member.id == user_id for member in project.members):
        return project

    project.members.append(user)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


async def remove_member_from_project(
    session: AsyncSession,
    project: Project,
    user_id: int,
) -> Project:
    for member in list(project.members):
        if member.id == user_id:
            project.members.remove(member)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project
