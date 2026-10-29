import uuid

import app.routers.donations as donations_router
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


def test_donor_can_upload_and_delete_owned_image(monkeypatch) -> None:
    donor = register_donor()
    headers = {"Authorization": "Bearer " + donor["access_token"]}
    assert client.post("/api/donations/profile", headers=headers, json=profile_payload()).status_code == 201
    created = client.post("/api/donations", headers=headers, json=donation_payload())
    donation_id = created.json()["id"]

    monkeypatch.setattr(
        donations_router,
        "upload_image",
        lambda file_object, folder: {
            "asset_id": "asset-test-1",
            "public_id": "shiksha-setu/test-image",
            "secure_url": "https://res.cloudinary.com/test/image/upload/test-image.png",
            "format": "png",
            "bytes": len(file_object),
            "width": 120,
            "height": 80,
        },
    )
    deleted: list[str] = []
    monkeypatch.setattr(donations_router, "delete_image", deleted.append)

    uploaded = client.post(
        f"/api/donations/{donation_id}/images",
        headers=headers,
        files={"file": ("book.png", b"fake-png-content", "image/png")},
    )
    assert uploaded.status_code == 201
    image_id = uploaded.json()["id"]
    assert uploaded.json()["secure_url"].startswith("https://")

    listed = client.get(f"/api/donations/{donation_id}/images", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == image_id

    removed = client.delete(f"/api/donations/{donation_id}/images/{image_id}", headers=headers)
    assert removed.status_code == 204
    assert deleted == ["shiksha-setu/test-image"]


def test_image_upload_rejects_unsupported_type_and_large_files(monkeypatch) -> None:
    donor = register_donor()
    headers = {"Authorization": "Bearer " + donor["access_token"]}
    assert client.post("/api/donations/profile", headers=headers, json=profile_payload()).status_code == 201
    created = client.post("/api/donations", headers=headers, json=donation_payload())
    donation_id = created.json()["id"]
    monkeypatch.setattr(donations_router, "upload_image", lambda *args, **kwargs: {})

    unsupported = client.post(
        f"/api/donations/{donation_id}/images",
        headers=headers,
        files={"file": ("notes.txt", b"not-an-image", "text/plain")},
    )
    assert unsupported.status_code == 415

    oversized = client.post(
        f"/api/donations/{donation_id}/images",
        headers=headers,
        files={"file": ("large.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
    )
    assert oversized.status_code == 413
