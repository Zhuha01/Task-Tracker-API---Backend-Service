from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import TaskStatus

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class TaskStatusHistory(Base):
    __tablename__ = "task_status_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    old_status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False),
    )
    new_status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False),
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    task: Mapped["Task"] = relationship(back_populates="history")
    user: Mapped["User"] = relationship()
