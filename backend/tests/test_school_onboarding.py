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
def clear_database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    yield
    with test_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


def register_school() -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "school@example.com",
            "username": "school-owner",
            "password": "a-strong-password",
            "role": "school",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_admin() -> str:
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
    response = client.post(
        "/api/auth/login",
        json={"identifier": "admin", "password": "a-strong-password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_school_can_submit_verification_and_admin_can_decide() -> None:
    school = register_school()
    school_headers = {"Authorization": f"Bearer {school['access_token']}"}

    profile = client.post(
        "/api/schools/profile",
        headers=school_headers,
        json={
            "name": "Fictional Valley School",
            "description": "A fictional school for integration tests.",
            "city": "Jaipur",
            "region": "Rajasthan",
            "website": "https://example.com/school",
        },
    )
    assert profile.status_code == 201
    assert profile.json()["verification_status"] == "pending"

    submission = client.post(
        "/api/schools/profile/verification",
        headers=school_headers,
        json={
            "registration_reference": "FICTIONAL-123",
            "evidence_description": "Fictional registration evidence supplied for testing.",
        },
    )
    assert submission.status_code == 201
    verification_id = submission.json()["id"]

    duplicate = client.post(
        "/api/schools/profile/verification",
        headers=school_headers,
        json={
            "registration_reference": "FICTIONAL-124",
            "evidence_description": "Another fictional submission.",
        },
    )
    assert duplicate.status_code == 409

    admin_headers = {"Authorization": f"Bearer {create_admin()}"}
    review_queue = client.get("/api/admin/school-verifications", headers=admin_headers)
    assert review_queue.status_code == 200
    assert review_queue.json()[0]["id"] == verification_id

    decision = client.post(
        f"/api/admin/school-verifications/{verification_id}/decision",
        headers=admin_headers,
        json={"status": "approved", "reason": "Evidence reviewed by the administrator."},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"

    updated_profile = client.get("/api/schools/profile", headers=school_headers)
    assert updated_profile.status_code == 200
    assert updated_profile.json()["verification_status"] == "approved"

    audit_events = client.get("/api/admin/audit-events", headers=admin_headers)
    assert audit_events.status_code == 200
    assert {event["action"] for event in audit_events.json()} >= {
        "school.profile_created",
        "school.verification_submitted",
        "school.verification_approved",
    }


def test_non_school_cannot_access_school_onboarding() -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "donor@example.com",
            "username": "donor",
            "password": "a-strong-password",
            "role": "donor",
        },
    )
    assert response.status_code == 201

    forbidden = client.get(
        "/api/schools/profile",
        headers={"Authorization": f"Bearer {response.json()['access_token']}"},
    )
    assert forbidden.status_code == 403
