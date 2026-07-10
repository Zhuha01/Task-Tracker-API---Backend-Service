from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.router import api_router
from app.core.cache import close_redis
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIdMiddleware

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_redis()


limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    cast(Any, _rate_limit_exceeded_handler),
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestIdMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
@limiter.exempt
async def health(request: Request) -> dict[str, str]:
    return {"status": "ok"}


logger.info(
    "application_started", project=settings.PROJECT_NAME, version=settings.VERSION
)
