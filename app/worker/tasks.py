from __future__ import annotations

from app.core.celery_app import celery_app
from app.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="send_mock_email_task")
def send_mock_email_task(email: str, message: str) -> None:
    logger.info("mock_email_sent", email=email, message=message)
