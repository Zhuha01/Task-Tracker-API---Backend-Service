from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TaskPriority, TaskStatus
from app.models.history import TaskStatusHistory
from app.models.notification import Notification
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


async def test_create_task_rejects_non_member_assignee(
    client: AsyncClient,
    test_project,
    non_member_user: User,
    user_token_headers: dict[str, str],
):
    response = await client.post(
        f"/api/v1/projects/{test_project.id}/tasks",
        headers=user_token_headers,
        json={
            "title": "Bad assignee",
            "assignee_id": non_member_user.id,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Assignee must be a project member"


async def test_create_task_with_member_assignee_notifies(
    client: AsyncClient,
    db_session: AsyncSession,
    test_project,
    member_user: User,
    user_token_headers: dict[str, str],
    mock_celery_email: list[tuple[str, str]],
):
    response = await client.post(
        f"/api/v1/projects/{test_project.id}/tasks",
        headers=user_token_headers,
        json={
            "title": "Assigned task",
            "description": "needs work",
            "priority": TaskPriority.high.value,
            "assignee_id": member_user.id,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["assignee_id"] == member_user.id
    assert body["priority"] == TaskPriority.high.value

    result = await db_session.execute(
        select(Notification).where(Notification.user_id == member_user.id)
    )
    notifications = list(result.scalars().all())
    assert len(notifications) == 1
    assert "Assigned task" in notifications[0].message
    assert len(mock_celery_email) == 1
    assert mock_celery_email[0][0] == member_user.email


async def test_list_tasks_filter_and_sort(
    client: AsyncClient,
    test_project,
    user_token_headers: dict[str, str],
):
    await client.post(
        f"/api/v1/projects/{test_project.id}/tasks",
        headers=user_token_headers,
        json={"title": "Low task", "priority": TaskPriority.low.value},
    )
    await client.post(
        f"/api/v1/projects/{test_project.id}/tasks",
        headers=user_token_headers,
        json={"title": "High task", "priority": TaskPriority.high.value},
    )

    filtered = await client.get(
        f"/api/v1/projects/{test_project.id}/tasks",
        headers=user_token_headers,
        params={"priority": TaskPriority.high.value, "sort_by": "priority"},
    )
    assert filtered.status_code == 200
    titles = [t["title"] for t in filtered.json()]
    assert "High task" in titles
    assert "Low task" not in titles


async def test_search_tasks(
    client: AsyncClient,
    test_project,
    test_task: Task,
    user_token_headers: dict[str, str],
):
    response = await client.get(
        f"/api/v1/projects/{test_project.id}/tasks/search",
        headers=user_token_headers,
        params={"q": "Test Task", "limit": 10},
    )
    assert response.status_code == 200
    ids = [t["id"] for t in response.json()]
    assert test_task.id in ids


async def test_get_patch_delete_task(
    client: AsyncClient,
    test_task: Task,
    user_token_headers: dict[str, str],
):
    fetched = await client.get(
        f"/api/v1/tasks/{test_task.id}",
        headers=user_token_headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Test Task"

    patched = await client.patch(
        f"/api/v1/tasks/{test_task.id}",
        headers=user_token_headers,
        json={"title": "Updated title"},
    )
    assert patched.status_code == 200
    assert patched.json()["title"] == "Updated title"

    deleted = await client.delete(
        f"/api/v1/tasks/{test_task.id}",
        headers=user_token_headers,
    )
    assert deleted.status_code == 204
