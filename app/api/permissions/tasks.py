from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

from app.api.permissions.projects import check_project_member
from app.models.project import Project
from app.models.task import Task
from app.models.user import User


def check_task_access(user: User, task: Task) -> None:
    check_project_member(user, task.project)


def check_assignee_is_project_member(
    project: Project, assignee_id: Optional[int]
) -> None:
    if assignee_id is None:
        return
    if project.owner_id == assignee_id:
        return
    if any(member.id == assignee_id for member in project.members):
        return
    raise HTTPException(
        status_code=400,
        detail="Assignee must be a project member",
    )
