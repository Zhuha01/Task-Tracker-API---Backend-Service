"""Seed demo users, projects, and tasks for API testing."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TypedDict

from app.crud.project import add_member_to_project, create_project, get_project
from app.crud.task import create_task, update_task_status
from app.crud.user import create_user, get_user_by_email
from app.db.session import AsyncSessionLocal
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate
from app.schemas.user import UserCreate

PASSWORD = "password123"


class TaskSeedData(TypedDict):
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    assignee_email: str | None
    deadline_days: int | None


class ProjectSeedData(TypedDict):
    name: str
    description: str
    owner_email: str
    member_emails: list[str]
    tasks: list[TaskSeedData]


class CreatedProjectSummary(TypedDict):
    id: int
    name: str
    owner: str
    task_count: int


USERS = [
    ("alice@example.com", "Alice"),
    ("bob@example.com", "Bob"),
    ("carol@example.com", "Carol"),
    ("dave@example.com", "Dave"),
]

PROJECTS: list[ProjectSeedData] = [
    {
        "name": "Website Redesign",
        "description": "Redesign company website and landing pages",
        "owner_email": "alice@example.com",
        "member_emails": ["bob@example.com", "carol@example.com"],
        "tasks": [
            {
                "title": "Design homepage",
                "description": "Create Figma mockups for the new homepage",
                "priority": TaskPriority.high,
                "status": TaskStatus.todo,
                "assignee_email": "bob@example.com",
                "deadline_days": 7,
            },
            {
                "title": "Setup CI/CD",
                "description": "Configure GitHub Actions pipeline",
                "priority": TaskPriority.medium,
                "status": TaskStatus.in_progress,
                "assignee_email": "carol@example.com",
                "deadline_days": 14,
            },
            {
                "title": "Write API docs",
                "description": "Document all public endpoints in OpenAPI",
                "priority": TaskPriority.low,
                "status": TaskStatus.done,
                "assignee_email": None,
                "deadline_days": 21,
            },
            {
                "title": "Review mockups",
                "description": "Stakeholder review of design proposals",
                "priority": TaskPriority.medium,
                "status": TaskStatus.todo,
                "assignee_email": "alice@example.com",
                "deadline_days": 5,
            },
            {
                "title": "Deploy staging",
                "description": "Deploy latest build to staging environment",
                "priority": TaskPriority.high,
                "status": TaskStatus.in_progress,
                "assignee_email": "bob@example.com",
                "deadline_days": 3,
            },
        ],
    },
    {
        "name": "Mobile App",
        "description": "iOS and Android task tracker app",
        "owner_email": "bob@example.com",
        "member_emails": ["dave@example.com"],
        "tasks": [
            {
                "title": "Auth flow",
                "description": "Implement login and registration screens",
                "priority": TaskPriority.high,
                "status": TaskStatus.todo,
                "assignee_email": "dave@example.com",
                "deadline_days": 10,
            },
            {
                "title": "Push notifications",
                "description": "Integrate FCM and APNs",
                "priority": TaskPriority.medium,
                "status": TaskStatus.in_progress,
                "assignee_email": "bob@example.com",
                "deadline_days": 20,
            },
            {
                "title": "Bug fix login",
                "description": "Fix token refresh on app resume",
                "priority": TaskPriority.low,
                "status": TaskStatus.done,
                "assignee_email": "dave@example.com",
                "deadline_days": None,
            },
        ],
    },
    {
        "name": "Internal Tools",
        "description": "Admin dashboard and reporting tools",
        "owner_email": "carol@example.com",
        "member_emails": [],
        "tasks": [
            {
                "title": "Migrate database",
                "description": "Run Alembic migrations on production",
                "priority": TaskPriority.medium,
                "status": TaskStatus.todo,
                "assignee_email": None,
                "deadline_days": 30,
            },
            {
                "title": "Update dependencies",
                "description": "Bump FastAPI, SQLAlchemy, and security patches",
                "priority": TaskPriority.low,
                "status": TaskStatus.in_progress,
                "assignee_email": "carol@example.com",
                "deadline_days": 15,
            },
        ],
    },
]


async def get_or_create_user(session, email: str, name: str):
    user = await get_user_by_email(session, email)
    if user is not None:
        print(f"  user exists: {email} (id={user.id})")
        return user
    user = await create_user(
        session,
        UserCreate(email=email, name=name, password=PASSWORD),
    )
    print(f"  created user: {email} (id={user.id}, role={user.role.value})")
    return user


async def seed() -> None:
    now = datetime.now(timezone.utc)
    email_to_id: dict[str, int] = {}
    created_projects: list[CreatedProjectSummary] = []

    async with AsyncSessionLocal() as session:
        print("=== Users ===")
        for email, name in USERS:
            user = await get_or_create_user(session, email, name)
            email_to_id[email] = user.id

        print("\n=== Projects & Tasks ===")
        for project_data in PROJECTS:
            owner_id = email_to_id[project_data["owner_email"]]
            project_in = ProjectCreate(
                name=project_data["name"],
                description=project_data["description"],
            )
            project = await create_project(session, project_in, owner_id=owner_id)

            refreshed = await get_project(session, project.id)
            assert refreshed is not None
            project = refreshed

            for member_email in project_data["member_emails"]:
                member_id = email_to_id[member_email]
                await add_member_to_project(session, project, user_id=member_id)
                refreshed = await get_project(session, project.id)
                assert refreshed is not None
                project = refreshed

            print(
                f"\n  project: {project.name} (id={project.id}, "
                f"owner={project_data['owner_email']})"
            )

            for task_data in project_data["tasks"]:
                assignee_id = None
                if task_data["assignee_email"]:
                    assignee_id = email_to_id[task_data["assignee_email"]]

                deadline = None
                if task_data["deadline_days"] is not None:
                    deadline = now + timedelta(days=task_data["deadline_days"])

                task_in = TaskCreate(
                    title=task_data["title"],
                    description=task_data["description"],
                    priority=task_data["priority"],
                    deadline=deadline,
                    assignee_id=assignee_id,
                )
                task = await create_task(
                    session,
                    project_id=project.id,
                    author_id=owner_id,
                    task_in=task_in,
                )

                target_status = task_data["status"]
                if target_status != TaskStatus.todo:
                    await update_task_status(
                        session,
                        task.id,
                        target_status,
                        owner_id,
                    )

                print(
                    f"    task: {task_data['title']} "
                    f"(id={task.id}, status={target_status.value}, "
                    f"priority={task_data['priority'].value})"
                )

            created_projects.append(
                {
                    "id": project.id,
                    "name": project.name,
                    "owner": project_data["owner_email"],
                    "task_count": len(project_data["tasks"]),
                }
            )

    print("\n=== Summary ===")
    print(f"Password for all users: {PASSWORD}")
    print("\nUsers:")
    for email, name in USERS:
        print(f"  - {email} ({name})")
    print("\nProjects (for GET /api/v1/projects/{{id}}/tasks):")
    for p in created_projects:
        print(
            f"  - id={p['id']}: {p['name']} "
            f"({p['task_count']} tasks, owner={p['owner']})"
        )
    print("\nExample:")
    print(
        "  1. POST /api/v1/auth/login "
        "(username=alice@example.com, password=password123)"
    )
    print("  2. GET  /api/v1/projects/1/tasks")
    print(
        "  3. GET  /api/v1/projects/1/tasks"
        "?status=todo&priority=high&sort_by=deadline"
    )


if __name__ == "__main__":
    asyncio.run(seed())
