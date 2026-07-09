from __future__ import annotations

from fastapi import HTTPException

from app.api.permissions.users import is_admin
from app.models.project import Project
from app.models.user import User

_FORBIDDEN = HTTPException(status_code=403, detail="Not enough permissions")


def check_project_owner(user: User, project: Project) -> None:
    if not is_admin(user) and project.owner_id != user.id:
        raise _FORBIDDEN


def check_project_member(user: User, project: Project) -> None:
    if is_admin(user) or project.owner_id == user.id:
        return
    if any(member.id == user.id for member in project.members):
        return
    raise _FORBIDDEN


def check_project_edit(user: User, project: Project) -> None:
    check_project_owner(user, project)
