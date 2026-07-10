from __future__ import annotations

from app.api.permissions.exception.http_exception import FORBIDDEN
from app.api.permissions.users import is_admin
from app.models.notification import Notification
from app.models.user import User


def check_notification_access(user: User, notification: Notification) -> None:
    if is_admin(user):
        return
    if notification.user_id != user.id:
        raise FORBIDDEN
