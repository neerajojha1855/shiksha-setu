import uuid

from app.db import get_db
from app.main import app
from app.matching import evaluate_match
from app.models.donation import Donation
from app.models.need import Need
from app.models.school import School, VerificationStatus
from test_donations import donation_payload, profile_payload, register_donor
from test_needs import need_payload, register_school_for_needs
from test_school_onboarding import client


def test_matching_uses_hard_gates_and_explainable_scoring() -> None:
    need = Need(
        category="textbooks",
        quantity_requested=50,
        quantity_fulfilled=0,
        condition="good",
        urgency="high",
        priority="high",
        city="Jaipur",
        region="Rajasthan",
    )
    donation = Donation(
        category="TextBooks",
        quantity_available=60,
        quantity_reserved=0,
        condition="new",
        city="Jaipur",
        region="Rajasthan",
        delivery_available=False,
        pickup_available=True,
    )
    evaluation = evaluate_match(need, donation)
    assert evaluation is not None
    assert evaluation.score == 90
    assert evaluation.factors["same_city"] is True
    assert "enough inventory" in evaluation.explanation

    incompatible = Donation(
        category="computers",
        quantity_available=60,
        quantity_reserved=0,
        condition="new",
        city="Jaipur",
        region="Rajasthan",
    )
    assert evaluate_match(need, incompatible) is None


def test_school_can_generate_and_donor_can_accept_match() -> None:
    school = register_school_for_needs()
    session = next(app.dependency_overrides[get_db]())
    try:
        profile = session.get(School, uuid.UUID(school["school_id"]))
        assert profile is not None
        profile.verification_status = VerificationStatus.approved
        session.commit()
    finally:
        session.close()

    school_headers = {"Authorization": f"Bearer {school['token']}"}
    matching_need = {**need_payload(), "title": "Science books for matching", "category": "science-books"}
    created_need = client.post("/api/needs", headers=school_headers, json=matching_need)
    assert created_need.status_code == 201
    need_id = created_need.json()["id"]
    assert client.post(f"/api/needs/{need_id}/publish", headers=school_headers).status_code == 200

    donor = register_donor()
    donor_headers = {"Authorization": f"Bearer {donor['access_token']}"}
    assert client.post("/api/donations/profile", headers=donor_headers, json=profile_payload()).status_code == 201
    matching_donation = {**donation_payload(), "title": "Science books donation", "category": "science-books"}
    created_donation = client.post("/api/donations", headers=donor_headers, json=matching_donation)
    assert created_donation.status_code == 201

    generated = client.post(f"/api/matches/generate/{need_id}", headers=school_headers)
    assert generated.status_code == 200
    assert len(generated.json()) == 1
    match = generated.json()[0]
    assert match["status"] == "proposed"
    assert match["score"] == 80
    assert match["match_factors"]["category_match"] is True

    donor_matches = client.get("/api/matches/mine", headers=donor_headers)
    assert donor_matches.status_code == 200
    assert donor_matches.json()[0]["id"] == match["id"]

    accepted = client.post(f"/api/matches/{match['id']}/accept", headers=donor_headers)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    repeated = client.post(f"/api/matches/generate/{need_id}", headers=school_headers)
    assert repeated.status_code == 200
    assert repeated.json() == []
    assert client.post(f"/api/needs/{need_id}/close", headers=school_headers).status_code == 200


def test_only_owned_need_can_generate_matches() -> None:
    school = register_school_for_needs()
    other_school = register_school_for_needs()
    owner_headers = {"Authorization": f"Bearer {school['token']}"}
    created = client.post("/api/needs", headers=owner_headers, json=need_payload())
    assert created.status_code == 201
    headers = {"Authorization": f"Bearer {other_school['token']}"}
    assert client.post(
        "/api/matches/generate/" + created.json()["id"], headers=headers
    ).status_code == 403
