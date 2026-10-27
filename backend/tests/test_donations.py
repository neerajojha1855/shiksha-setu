import uuid

from test_school_onboarding import client


def register_donor() -> dict:
    identifier = uuid.uuid4().hex[:10]
    response = client.post(
        "/api/auth/register",
        json={
            "email": f"donor-{identifier}@example.com",
            "username": f"donor-{identifier}",
            "password": "a-strong-password",
            "role": "donor",
        },
    )
    assert response.status_code == 201
    return response.json()


def profile_payload() -> dict:
    return {
        "display_name": "Fictional Learning Supporter",
        "organization": "Fictional Community Group",
        "bio": "Fictional donor profile for integration tests.",
        "city": "Jaipur",
        "region": "Rajasthan",
    }


def donation_payload() -> dict:
    return {
        "title": "Used science textbooks",
        "description": "Good-condition science textbooks for secondary classrooms.",
        "category": "textbooks",
        "quantity_available": 30,
        "condition": "good",
        "availability": "Available this month",
        "pickup_available": True,
        "delivery_available": False,
        "city": "Jaipur",
        "region": "Rajasthan",
    }


def test_donor_can_create_list_and_withdraw_donation() -> None:
    donor = register_donor()
    headers = {"Authorization": "Bearer " + donor["access_token"]}

    profile = client.post("/api/donations/profile", headers=headers, json=profile_payload())
    assert profile.status_code == 201

    created = client.post("/api/donations", headers=headers, json=donation_payload())
    assert created.status_code == 201
    donation_id = created.json()["id"]

    public = client.get("/api/donations?search=science")
    assert public.status_code == 200
    assert public.json()["total"] == 1
    assert public.json()["items"][0]["quantity_remaining"] == 30

    withdrawn = client.post(f"/api/donations/{donation_id}/withdraw", headers=headers)
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"
    assert client.get("/api/donations?search=science").json()["total"] == 0


def test_donation_requires_profile_and_owner_authorization() -> None:
    donor = register_donor()
    donor_headers = {"Authorization": "Bearer " + donor["access_token"]}
    missing_profile = client.post("/api/donations", headers=donor_headers, json=donation_payload())
    assert missing_profile.status_code == 404

    client.post("/api/donations/profile", headers=donor_headers, json=profile_payload())
    created = client.post("/api/donations", headers=donor_headers, json=donation_payload())
    donation_id = created.json()["id"]

    other_donor = register_donor()
    other_headers = {"Authorization": "Bearer " + other_donor["access_token"]}
    assert client.post(
        f"/api/donations/{donation_id}/withdraw", headers=other_headers
    ).status_code == 403
