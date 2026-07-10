from __future__ import annotations

import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="send_mock_email_task")
def send_mock_email_task(email: str, message: str) -> None:
    logger.info("MOCK EMAIL sent to %s: %s", email, message)
