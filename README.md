# Task Tracker API

Backend service for managing users, projects, and tasks (simplified Jira/Trello-style API).

**Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Alembic, Celery + Redis, Docker Compose.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

On startup the API container runs `alembic upgrade head`, then serves the app.


| Service    | URL                                                          |
| ---------- | ------------------------------------------------------------ |
| API        | [http://localhost:8000](http://localhost:8000)               |
| Swagger UI | [http://localhost:8000/docs](http://localhost:8000/docs)     |
| ReDoc      | [http://localhost:8000/redoc](http://localhost:8000/redoc)   |
| Health     | [http://localhost:8000/health](http://localhost:8000/health) |


Compose services: `db` (PostgreSQL 16), `redis`, `api`, `worker` (Celery).

### Local development (without Docker for the app)

1. Start PostgreSQL and Redis (or use Compose for infra only).
2. Copy `.env.example` → `.env` and point `POSTGRES_HOST` / `REDIS_HOST` at your instances.
3. Install deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

1. Migrate and run:

```bash
alembic upgrade head
uvicorn app.main:app --reload
celery -A app.core.celery_app:celery_app worker --loglevel=info
```



### Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

Integration tests use Testcontainers (Docker required). Coverage gate: **70%**.

### Lint / types

```bash
ruff format .
ruff check .
mypy app/
```

CI (GitHub Actions) runs format check, ruff, mypy, pytest with coverage, and a Docker build on every PR/push to `main`.

## API overview

Base path: `/api/v1`


| Area          | Endpoints                                                                           |
| ------------- | ----------------------------------------------------------------------------------- |
| Auth          | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`               |
| Users         | `GET/PATCH/DELETE /users/me`, admin user management                                 |
| Projects      | CRUD `/projects`, members `POST/DELETE /projects/{id}/members/{user_id}`            |
| Tasks         | CRUD under project / by id, `PATCH /tasks/{id}/status`, filters + sort + pagination |
| Search        | `GET /projects/{id}/tasks/search?q=`                                                |
| Comments      | CRUD on tasks / by comment id                                                       |
| Activity      | `GET /projects/{id}/activity`                                                       |
| Notifications | `GET /notifications/unread`, `PATCH /notifications/{id}/read`                       |
| Live updates  | `WS /projects/{id}/ws?token=<access_jwt>` — task status changes                     |


Interactive docs: [Swagger UI](http://localhost:8000/docs).

## Design decisions

- **First registered user:** Becomes `admin` when the users table is empty (bootstrap); subsequent registrations get `user`.
- **Search:** PostgreSQL `ILIKE` on title/description (simpler than `tsvector` for this scope; still project-scoped and paginated).
- **Project owner vs members:** Owner is stored as `owner_id`. Access checks treat owner as a member without requiring a row in `project_members`.
- **Admin role:** Admins bypass project membership checks for read/write where permissions allow.
- **Logout:** Returns `204` without a token blacklist. Access tokens expire via JWT TTL; clients discard tokens. Documented trade-off vs Redis revoke list.
- **Status history:** Written only via `PATCH /tasks/{id}/status`, not via general task update (status is not in `TaskUpdate`).
- **Notifications:** On assignee change (not self-assign), create an in-app notification and enqueue a Celery mock email (log only, no SMTP).
- **Rate limiting:** Applied globally via SlowAPI (default in-memory limiter suitable for single-instance demo).
- **Logging:** Structured logs via `structlog` with a per-request `request_id` middleware.
- **Task list cache:** Redis caches `GET /projects/{id}/tasks` responses (TTL 60s). Keys include filters/sort/pagination. Mutations (create/update/status/delete) invalidate `tasks:list:{project_id}:`*. Disable with `CACHE_ENABLED=false`.
- **WebSocket:** `WS /api/v1/projects/{id}/ws?token=...` broadcasts `{event: task_status_changed, ...}` after a successful status PATCH. Auth uses the same JWT access token; membership is checked on connect.



## AI usage

AI tools (Cursor) accelerated scaffolding and boilerplate. Human review focused on:

- Permission model (owner / member / admin / comment author)
- Assignee-must-be-member validation and status history
- Celery notification side effects
- Docker/Compose DX (migrations on start, multi-stage image, healthchecks)
- Integration tests for core business flows and coverage gate

Generated code was checked by running the suite, exercising Swagger flows, and reviewing permission edge cases manually.

## Project layout

```
app/
  api/          # routers, deps, permissions
  core/         # settings, security, celery, cache, ws, logging, middleware
  crud/         # DB operations
  db/           # async session
  models/       # SQLAlchemy models
  schemas/      # Pydantic v2
  worker/       # Celery tasks
alembic/        # migrations
docs/           # Postman collection
tests/          # pytest + testcontainers
scripts/        # Docker entrypoint (migrations)
```

