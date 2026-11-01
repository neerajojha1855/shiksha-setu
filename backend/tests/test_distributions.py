import uuid

from app.db import get_db
from app.main import app
from app.models.school import School, VerificationStatus
from app.models.user import User, UserRole
from app.auth import hash_password
from test_donations import donation_payload, profile_payload, register_donor
from test_needs import need_payload, register_school_for_needs
from test_school_onboarding import client


def _approve_school(school_id: str) -> None:
    session = next(app.dependency_overrides[get_db]())
    try:
        school = session.get(School, uuid.UUID(school_id))
        assert school is not None
        school.verification_status = VerificationStatus.approved
        session.commit()
    finally:
        session.close()


def _create_admin() -> str:
    session = next(app.dependency_overrides[get_db]())
    try:
        session.add(User(
            email="distribution-admin@example.com",
            username="distribution-admin",
            password_hash=hash_password("a-strong-password"),
            role=UserRole.administrator,
        ))
        session.commit()
    finally:
        session.close()
    response = client.post(
        "/api/auth/login",
        json={"identifier": "distribution-admin", "password": "a-strong-password"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_distribution_workflow_is_idempotent_and_auditable() -> None:
    school = register_school_for_needs()
    _approve_school(school["school_id"])
    school_headers = {"Authorization": "Bearer " + school["token"]}

    created_need = client.post(
        "/api/needs",
        headers=school_headers,
        json={**need_payload(), "title": "Distribution workflow need", "category": "distribution-books"},
    )
    assert created_need.status_code == 201
    need_id = created_need.json()["id"]
    assert client.post(f"/api/needs/{need_id}/publish", headers=school_headers).status_code == 200

    donor = register_donor()
    donor_headers = {"Authorization": "Bearer " + donor["access_token"]}
    assert client.post("/api/donations/profile", headers=donor_headers, json=profile_payload()).status_code == 201
    created_donation = client.post(
        "/api/donations",
        headers=donor_headers,
        json={**donation_payload(), "title": "Distribution workflow donation", "category": "distribution-books"},
    )
    assert created_donation.status_code == 201

    generated = client.post(f"/api/matches/generate/{need_id}", headers=school_headers)
    assert generated.status_code == 200
    match_id = generated.json()[0]["id"]
    assert client.post(f"/api/matches/{match_id}/accept", headers=donor_headers).status_code == 200

    distributions = client.get("/api/distributions/mine", headers=donor_headers)
    assert distributions.status_code == 200
    distribution = distributions.json()[0]
    distribution_id = distribution["id"]
    assert distribution["status"] == "reserved"

    assert client.post(f"/api/distributions/{distribution_id}/dispatch", headers=donor_headers).status_code == 200
    dispatched_again = client.post(f"/api/distributions/{distribution_id}/dispatch", headers=donor_headers)
    assert dispatched_again.status_code == 200
    assert dispatched_again.json()["status"] == "in_transit"
    assert client.post(f"/api/distributions/{distribution_id}/mark-delivered", headers=donor_headers).status_code == 200
    assert client.post(f"/api/distributions/{distribution_id}/confirm-receipt", headers=school_headers).status_code == 200

    admin_headers = {"Authorization": "Bearer " + _create_admin()}
    assert client.post(f"/api/distributions/{distribution_id}/verify", headers=admin_headers).status_code == 200
    history = client.get(f"/api/distributions/{distribution_id}/history", headers=school_headers)
    assert history.status_code == 200
    assert [item["to_status"] for item in history.json()] == [
        "reserved", "in_transit", "delivered_pending_confirmation", "received", "verified"
    ]
