from __future__ import annotations

from app.api.permissions.exception.http_exception import FORBIDDEN
from app.api.permissions.tasks import check_task_access
from app.models.comment import Comment
from app.models.user import User


def check_comment_access(user: User, comment: Comment) -> None:
    check_task_access(user, comment.task)


def check_comment_author(user: User, comment: Comment) -> None:
    if comment.user_id != user.id:
        raise FORBIDDEN
