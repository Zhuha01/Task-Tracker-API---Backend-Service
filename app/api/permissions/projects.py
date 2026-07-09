from __future__ import annotations

from fastapi import HTTPException

from app.api.permissions.users import is_admin
from app.models.project import Project
from app.models.user import User

_FORBIDDEN = HTTPException(status_code=403, detail="Not enough permissions")


def is_project_member_or_owner(user: User, project: Project) -> bool:
    if project.owner_id == user.id:
        return True
    return any(member.id == user.id for member in project.members)


def is_user_id_project_member_or_owner(project: Project, user_id: int) -> bool:
    if project.owner_id == user_id:
        return True
    return any(member.id == user_id for member in project.members)


def check_project_owner(user: User, project: Project) -> None:
    if is_admin(user):
        return
    if project.owner_id != user.id:
        raise _FORBIDDEN


def check_project_member(user: User, project: Project) -> None:
    if is_admin(user):
        return
    if not is_project_member_or_owner(user, project):
        raise _FORBIDDEN


def check_project_edit(user: User, project: Project) -> None:
    if is_admin(user):
        return
    if user.id != project.owner_id:
        raise _FORBIDDEN
