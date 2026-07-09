from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.permissions import check_project_member
from app.crud.activity import get_project_activity
from app.crud.project import get_project
from app.db.session import get_db
from app.models.user import User
from app.schemas.activity import ActivityEventRead

router = APIRouter(tags=["Activity"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


@router.get(
    "/projects/{project_id}/activity",
    response_model=List[ActivityEventRead],
)
async def list_activity(
    project_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    project = await get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    check_project_member(current_user, project)

    return await get_project_activity(
        session,
        project_id,
        skip=skip,
        limit=limit,
    )
