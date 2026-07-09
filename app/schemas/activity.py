from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from app.models.enums import TaskStatus


class ActivityEventType(str, Enum):
    task_created = "task_created"
    task_status_changed = "task_status_changed"
    comment_created = "comment_created"


class ActivityEventRead(BaseModel):
    event_type: ActivityEventType
    created_at: datetime
    actor_id: int
    task_id: int
    task_title: str
    source_id: int
    old_status: Optional[TaskStatus] = None
    new_status: Optional[TaskStatus] = None
    comment_text: Optional[str] = None
