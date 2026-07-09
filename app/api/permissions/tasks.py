from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from app.api.permissions.projects import (
    check_project_member,
    is_user_id_project_member_or_owner,
)
from app.api.permissions.users import is_admin
from app.models.project import Project
from app.models.task import Task
from app.models.user import User


def check_task_access(user: User, task: Task) -> None:
    if is_admin(user):
        return
    check_project_member(user, task.project)


def check_assignee_is_project_member(
    project: Project, assignee_id: Optional[int]
) -> None:
    if assignee_id is None:
        return
    if not is_user_id_project_member_or_owner(project, assignee_id):
        raise HTTPException(
            status_code=400,
            detail="Assignee must be a project member",
        )
