from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import hash_password
from app.db import Base, get_db
from app.main import app
from app.models.user import User, UserRole

test_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
Base.metadata.create_all(test_engine)


def override_get_db() -> Generator[Session, None, None]:
    with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None, None, None]:
    clear_database()
    yield
    clear_database()


def clear_database() -> None:
    with test_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


def register_user(username: str, role: str) -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "a-strong-password",
            "role": role,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_users_can_only_read_their_own_account() -> None:
    owner = register_user("owner", "donor")
    other_user = register_user("other", "school")

    own_response = client.get(
        f"/api/auth/users/{owner['user']['id']}",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert own_response.status_code == 200

    forbidden_response = client.get(
        f"/api/auth/users/{other_user['user']['id']}",
        headers={"Authorization": f"Bearer {owner['access_token']}"},
    )
    assert forbidden_response.status_code == 403


def test_only_administrators_can_list_users() -> None:
    donor = register_user("donor", "donor")
    forbidden_response = client.get(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {donor['access_token']}"},
    )
    assert forbidden_response.status_code == 403


def test_administrators_can_list_users() -> None:
    with TestSessionLocal() as session:
        session.add(
            User(
                email="admin@example.com",
                username="admin",
                password_hash=hash_password("a-strong-password"),
                role=UserRole.administrator,
            )
        )
        session.commit()

    login_response = client.post(
        "/api/auth/login",
        json={"identifier": "admin", "password": "a-strong-password"},
    )
    assert login_response.status_code == 200

    response = client.get(
        "/api/auth/users",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )
    assert response.status_code == 200
    assert [user["username"] for user in response.json()] == ["admin"]
