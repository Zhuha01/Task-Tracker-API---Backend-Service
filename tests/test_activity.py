from __future__ import annotations

from httpx import AsyncClient

from app.models.enums import TaskStatus
from app.models.task import Task


async def test_project_activity_feed(
    client: AsyncClient,
    test_project,
    test_task: Task,
    user_token_headers: dict[str, str],
):
    await client.patch(
        f"/api/v1/tasks/{test_task.id}/status",
        headers=user_token_headers,
        json={"status": TaskStatus.in_progress.value},
    )
    await client.post(
        f"/api/v1/tasks/{test_task.id}/comments",
        headers=user_token_headers,
        json={"text": "Activity comment"},
    )

    response = await client.get(
        f"/api/v1/projects/{test_project.id}/activity",
        headers=user_token_headers,
    )
    assert response.status_code == 200
    events = response.json()
    event_types = {e["event_type"] for e in events}
    assert "task_created" in event_types
    assert "task_status_changed" in event_types
    assert "comment_created" in event_types
