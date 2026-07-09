from __future__ import annotations

from fastapi import HTTPException

from app.models.enums import Role
from app.models.user import User

_FORBIDDEN = HTTPException(status_code=403, detail="Not enough permissions")


def is_admin(user: User) -> bool:
    return user.role == Role.admin


def check_admin(user: User) -> None:
    if not is_admin(user):
        raise _FORBIDDEN


def check_user_is_self(current_user: User, target_user_id: int) -> None:
    if is_admin(current_user):
        return
    if current_user.id != target_user_id:
        raise _FORBIDDEN


def check_can_delete_user(actor: User, target: User) -> None:
    if is_admin(target) and target.id != actor.id:
        raise _FORBIDDEN


def check_can_update_user(actor: User, target: User) -> None:
    check_user_is_self(actor, target.id)
    if is_admin(actor) and actor.id != target.id and is_admin(target):
        raise _FORBIDDEN


def check_role_change_in_payload(actor: User, role: Role | None) -> None:
    if role is None:
        return
    if is_admin(actor):
        return
    raise _FORBIDDEN


def check_forbid_role_in_me_payload(role: Role | None) -> None:
    if role is not None:
        raise _FORBIDDEN


def can_change_target_role(actor: User, target: User) -> bool:
    return is_admin(actor) and actor.id != target.id and not is_admin(target)
