from __future__ import annotations

from fastapi import HTTPException

from app.api.permissions.tasks import check_task_access
from app.models.comment import Comment
from app.models.user import User

_FORBIDDEN = HTTPException(status_code=403, detail="Not enough permissions")


def check_comment_access(user: User, comment: Comment) -> None:
    check_task_access(user, comment.task)


def check_comment_author(user: User, comment: Comment) -> None:
    if comment.user_id != user.id:
        raise _FORBIDDEN
