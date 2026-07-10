from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def mock_send_email(email: str, message: str) -> None:
    logger.info("MOCK EMAIL sent to %s: %s", email, message)
