import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

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
def clear_database() -> Generator[None, None, None]:
    yield
    with test_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


def test_register_login_me_refresh_and_logout() -> None:
    registration = client.post(
        "/api/auth/register",
        json={
            "email": "Test.User@example.com",
            "username": "test-user",
            "password": "a-strong-password",
            "role": "donor",
        },
    )

    assert registration.status_code == 201
    registered = registration.json()
    assert registered["user"]["email"] == "test.user@example.com"

    access_token = registered["access_token"]
    refresh_token = registered["refresh_token"]
    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == "test-user"

    login = client.post(
        "/api/auth/login",
        json={"identifier": "test.user@example.com", "password": "a-strong-password"},
    )
    assert login.status_code == 200

    refreshed = client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refreshed.status_code == 200
    rotated_refresh_token = refreshed.json()["refresh_token"]
    assert rotated_refresh_token != refresh_token

    old_refresh = client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert old_refresh.status_code == 401

    logout = client.post(
        "/api/auth/logout", json={"refresh_token": rotated_refresh_token}
    )
    assert logout.status_code == 204

    revoked_refresh = client.post(
        "/api/auth/refresh", json={"refresh_token": rotated_refresh_token}
    )
    assert revoked_refresh.status_code == 401


def test_administrator_registration_is_rejected() -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "admin@example.com",
            "username": "admin-user",
            "password": "a-strong-password",
            "role": "administrator",
        },
    )

    assert response.status_code == 403


def test_duplicate_registration_is_rejected() -> None:
    payload = {
        "email": f"{uuid.uuid4()}@example.com",
        "username": "same-user",
        "password": "a-strong-password",
        "role": "school",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201

    duplicate = client.post(
        "/api/auth/register",
        json={**payload, "email": f"{uuid.uuid4()}@example.com"},
    )
    assert duplicate.status_code == 409
