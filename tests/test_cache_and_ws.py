from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.core.cache import task_list_cache_key
from app.core.ws import ConnectionManager
from app.models.enums import TaskStatus
from app.models.task import Task
from app.models.user import User


def test_task_list_cache_key_is_stable() -> None:
    key = task_list_cache_key(
        7,
        status="todo",
        priority="high",
        assignee_id=3,
        sort_by="created_at",
        skip=0,
        limit=20,
    )
    assert key == "tasks:list:7:todo:high:3:created_at:0:20"


async def test_list_tasks_uses_cache_when_enabled(
    client: AsyncClient,
    test_project,
    user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    cached_payload = [
        {
            "id": 99,
            "title": "From cache",
            "description": None,
            "status": "todo",
            "priority": "medium",
            "deadline": None,
            "project_id": test_project.id,
            "author_id": 1,
            "assignee_id": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
    ]
    monkeypatch.setattr("app.core.cache.settings.CACHE_ENABLED", True)
    monkeypatch.setattr(
        "app.api.endpoints.tasks.cache_get_json",
        AsyncMock(return_value=cached_payload),
    )
    set_mock = AsyncMock()
    monkeypatch.setattr("app.api.endpoints.tasks.cache_set_json", set_mock)

    response = await client.get(
        f"/api/v1/projects/{test_project.id}/tasks",
        headers=user_token_headers,
    )
    assert response.status_code == 200
    assert response.json()[0]["title"] == "From cache"
    set_mock.assert_not_awaited()


async def test_create_task_invalidates_cache(
    client: AsyncClient,
    test_project,
    user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    invalidate = AsyncMock()
    monkeypatch.setattr("app.crud.task.invalidate_project_task_list", invalidate)

    response = await client.post(
        f"/api/v1/projects/{test_project.id}/tasks",
        headers=user_token_headers,
        json={"title": "Cache bust"},
    )
    assert response.status_code == 201
    invalidate.assert_awaited()
    assert invalidate.await_args is not None
    assert invalidate.await_args.args[0] == test_project.id


async def test_status_change_broadcasts_websocket_event(
    client: AsyncClient,
    test_task: Task,
    test_user: User,
    user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
):
    broadcast = AsyncMock()
    monkeypatch.setattr("app.api.endpoints.tasks.ws_manager.broadcast", broadcast)

    response = await client.patch(
        f"/api/v1/tasks/{test_task.id}/status",
        headers=user_token_headers,
        json={"status": TaskStatus.in_progress.value},
    )
    assert response.status_code == 200
    broadcast.assert_awaited_once()
    assert broadcast.await_args is not None
    project_id, message = broadcast.await_args.args
    assert project_id == test_task.project_id
    assert message["event"] == "task_status_changed"
    assert message["task_id"] == test_task.id
    assert message["status"] == TaskStatus.in_progress.value
    assert message["changed_by"] == test_user.id


async def test_connection_manager_broadcasts_to_subscribers() -> None:
    manager = ConnectionManager()
    received: list[dict[str, Any]] = []

    class FakeWebSocket:
        async def accept(self) -> None:
            return None

        async def send_json(self, data: dict[str, Any]) -> None:
            received.append(data)

    ws = FakeWebSocket()
    await manager.connect(1, ws)  # type: ignore[arg-type]
    await manager.broadcast(1, {"event": "task_status_changed", "task_id": 5})
    assert received == [{"event": "task_status_changed", "task_id": 5}]
    manager.disconnect(1, ws)  # type: ignore[arg-type]
