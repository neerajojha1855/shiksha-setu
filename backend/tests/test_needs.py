import uuid

from app.db import get_db
from app.main import app
from app.models.school import School, VerificationStatus
from test_school_onboarding import client


def register_school_for_needs() -> dict:
    identifier = uuid.uuid4().hex[:10]
    response = client.post(
        "/api/auth/register",
        json={
            "email": f"needs-school-{identifier}@example.com",
            "username": f"needs-school-{identifier}",
            "password": "a-strong-password",
            "role": "school",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    profile = client.post(
        "/api/schools/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Needs School", "city": "Jaipur", "region": "Rajasthan"},
    )
    assert profile.status_code == 201
    return {"token": token, "school_id": profile.json()["id"]}


def need_payload() -> dict:
    return {
        "title": "Mathematics textbooks",
        "description": "Current textbooks for secondary students.",
        "category": "textbooks",
        "quantity_requested": 50,
        "condition": "good",
        "urgency": "high",
        "priority": "high",
        "intended_use": "Classroom instruction and a lending library.",
        "city": "Jaipur",
        "region": "Rajasthan",
    }


def test_unapproved_school_can_create_but_not_publish_need() -> None:
    school = register_school_for_needs()
    headers = {"Authorization": f"Bearer {school['token']}"}
    created = client.post("/api/needs", headers=headers, json=need_payload())
    assert created.status_code == 201
    assert created.json()["status"] == "draft"

    published = client.post(f"/api/needs/{created.json()['id']}/publish", headers=headers)
    assert published.status_code == 403


def test_approved_school_can_publish_pause_close_and_public_list() -> None:
    school = register_school_for_needs()
    session = next(app.dependency_overrides[get_db]())
    try:
        profile = session.get(School, uuid.UUID(school["school_id"]))
        assert profile is not None
        profile.verification_status = VerificationStatus.approved
        session.commit()
    finally:
        session.close()

    headers = {"Authorization": f"Bearer {school['token']}"}
    created = client.post("/api/needs", headers=headers, json=need_payload())
    need_id = created.json()["id"]
    published = client.post(f"/api/needs/{need_id}/publish", headers=headers)
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    public = client.get("/api/needs?search=Mathematics&limit=10")
    assert public.status_code == 200
    assert [item["id"] for item in public.json()] == [need_id]

    paused = client.post(f"/api/needs/{need_id}/pause", headers=headers)
    assert paused.status_code == 200
    assert client.get("/api/needs", params={"search": "Mathematics"}).json() == []

    closed = client.post(f"/api/needs/{need_id}/close", headers=headers)
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
