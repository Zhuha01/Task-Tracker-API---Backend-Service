from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TaskStatus
from app.models.history import TaskStatusHistory
from app.models.task import Task
from app.models.user import User


async def test_update_task_status_creates_history_record(
    client: AsyncClient,
    db_session: AsyncSession,
    test_task: Task,
    test_user: User,
    user_token_headers: dict[str, str],
):
    new_status = TaskStatus.in_progress

    response = await client.patch(
        f"/api/v1/tasks/{test_task.id}/status",
        headers=user_token_headers,
        json={"status": new_status.value},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == test_task.id
    assert body["status"] == new_status.value

    result = await db_session.execute(
        select(TaskStatusHistory).where(TaskStatusHistory.task_id == test_task.id)
    )
    history_records = list(result.scalars().all())

    assert len(history_records) == 1
    history = history_records[0]
    assert history.task_id == test_task.id
    assert history.new_status == new_status
    assert history.old_status == TaskStatus.todo
    assert history.user_id == test_user.id
