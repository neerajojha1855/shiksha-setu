import uuid
from collections.abc import Generator

import pytest
from app.db import get_db
from app.db import Base
from app.main import app
from app.models.need import Need, NeedStatus
from app.models.school import School, VerificationStatus
from test_school_onboarding import client, test_engine
from test_needs import register_school_for_needs


@pytest.fixture(autouse=True)
def clear_database() -> Generator[None, None, None]:
    yield
    with test_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


def test_public_discovery_returns_verified_school_and_progress() -> None:
    school = register_school_for_needs()
    session = next(app.dependency_overrides[get_db]())
    try:
        profile = session.get(School, uuid.UUID(school["school_id"]))
        assert profile is not None
        profile.verification_status = VerificationStatus.approved
        need = Need(
            school_id=profile.id,
            title="Library readers",
            description="Large-print readers for the school library.",
            category="books",
            quantity_requested=20,
            quantity_fulfilled=5,
            condition="good",
            urgency="medium",
            priority="high",
            intended_use="Library lending collection.",
            city="Jaipur",
            region="Rajasthan",
            status=NeedStatus.published,
        )
        session.add(need)
        session.commit()
    finally:
        session.close()

    response = client.get("/api/needs/discover?search=Library")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["school_verification_status"] == "approved"
    assert body["items"][0]["fulfillment_percent"] == 25


def test_unpublished_or_unverified_needs_are_not_discoverable() -> None:
    school = register_school_for_needs()
    response = client.post(
        "/api/needs",
        headers={"Authorization": f"Bearer {school['token']}"},
        json={
            "title": "Private classroom request",
            "description": "This draft must not appear in public discovery.",
            "category": "supplies",
            "quantity_requested": 10,
            "condition": "new",
            "urgency": "low",
            "priority": "low",
            "intended_use": "Classroom use.",
            "city": "Jaipur",
            "region": "Rajasthan",
        },
    )
    assert response.status_code == 201
    response = client.get("/api/needs/discover?search=Private+classroom")
    assert response.status_code == 200
    assert response.json()["items"] == []
