"""In-memory WebSocket fan-out for project task status updates."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, project_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._rooms[project_id].add(websocket)

    def disconnect(self, project_id: int, websocket: WebSocket) -> None:
        self._rooms[project_id].discard(websocket)
        if not self._rooms[project_id]:
            del self._rooms[project_id]

    async def broadcast(self, project_id: int, message: dict[str, Any]) -> None:
        sockets = list(self._rooms.get(project_id, ()))
        dead: list[WebSocket] = []
        for websocket in sockets:
            try:
                await websocket.send_json(message)
            except Exception:
                dead.append(websocket)
        for websocket in dead:
            self.disconnect(project_id, websocket)
        if sockets:
            logger.info(
                "ws_broadcast",
                project_id=project_id,
                recipients=len(sockets) - len(dead),
            )


ws_manager = ConnectionManager()
