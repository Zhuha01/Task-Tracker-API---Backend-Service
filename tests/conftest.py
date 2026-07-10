from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.core.security import create_access_token, get_password_hash
from app.crud.project import create_project
from app.db.session import get_db
from app.main import app
from app.models import Base, Role, Task, TaskStatus
from app.models.user import User
from app.schemas.project import ProjectCreate

TEST_PASSWORD = "testpass123"


def _to_async_url(sync_url: str) -> str:
    if "+psycopg2" in sync_url:
        return sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    return sync_url.replace("postgresql://", "postgresql+asyncpg://")


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def async_database_url(postgres_container: PostgresContainer) -> str:
    return _to_async_url(postgres_container.get_connection_url())


@pytest.fixture(scope="session")
def _init_database(async_database_url: str) -> str:
    async def init_models() -> None:
        engine = create_async_engine(async_database_url, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(init_models())
    return async_database_url


@pytest.fixture
async def db_engine(async_database_url: str, _init_database: str):
    engine = create_async_engine(async_database_url, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        db_engine,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session

    async with db_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _create_user(
    session: AsyncSession,
    *,
    email: str,
    name: str,
    role: Role,
) -> User:
    user = User(
        email=email,
        name=name,
        hashed_password=get_password_hash(TEST_PASSWORD),
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    return await _create_user(
        db_session,
        email="admin@example.com",
        name="Admin User",
        role=Role.admin,
    )


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    return await _create_user(
        db_session,
        email="user@example.com",
        name="Test User",
        role=Role.user,
    )


@pytest.fixture
async def test_project(db_session: AsyncSession, test_user: User):
    return await create_project(
        db_session,
        ProjectCreate(name="Test Project", description="A test project"),
        owner_id=test_user.id,
    )


@pytest.fixture
async def test_task(db_session: AsyncSession, test_project, test_user: User) -> Task:
    task = Task(
        title="Test Task",
        description="A task for integration tests",
        status=TaskStatus.todo,
        project_id=test_project.id,
        author_id=test_user.id,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_token_headers(test_user: User) -> dict[str, str]:
    return _auth_headers(test_user)


@pytest.fixture
def admin_token_headers(admin_user: User) -> dict[str, str]:
    return _auth_headers(admin_user)


@pytest.fixture(autouse=True)
def mock_celery_email(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []

    def fake_delay(email: str, message: str) -> None:
        calls.append((email, message))

    monkeypatch.setattr(
        "app.crud.task.send_mock_email_task.delay",
        fake_delay,
    )
    return calls


@pytest.fixture(autouse=True)
def disable_redis_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.config.settings.CACHE_ENABLED", False)
    monkeypatch.setattr("app.core.cache.settings.CACHE_ENABLED", False)


@pytest.fixture
async def member_user(db_session: AsyncSession, test_project) -> User:
    from app.crud.project import add_member_to_project, get_project

    user = await _create_user(
        db_session,
        email="member@example.com",
        name="Member User",
        role=Role.user,
    )
    project = await get_project(db_session, test_project.id)
    assert project is not None
    await add_member_to_project(db_session, project, user_id=user.id)
    return user


@pytest.fixture
def member_token_headers(member_user: User) -> dict[str, str]:
    return _auth_headers(member_user)


@pytest.fixture
async def non_member_user(db_session: AsyncSession) -> User:
    return await _create_user(
        db_session,
        email="stranger@example.com",
        name="Non Member",
        role=Role.user,
    )


@pytest.fixture
def non_member_token_headers(non_member_user: User) -> dict[str, str]:
    return _auth_headers(non_member_user)
