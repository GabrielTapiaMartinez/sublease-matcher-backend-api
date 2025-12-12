from fastapi.testclient import TestClient

from sublease_matcher.api.main import app  # Adjust this import to your actual FastAPI app location

client = TestClient(app)

def assert_status(resp, expected):
    print("Status:", resp.status_code)
    try:
        print("Response JSON:", resp.json())
    except Exception:
        print("Response Text:", resp.text)
    assert resp.status_code == expected, f"Expected {expected}, got {resp.status_code}"

def test_profile_alias_get_put():
    # Test both GET /profiles/me and /seekers/me/profile aliases
    resp1 = client.get("/seekers/me/profile")
    resp2 = client.get("/profiles/me")
    print("GET /seekers/me/profile:", resp1.json())
    print("GET /profiles/me:", resp2.json())
    assert resp1.json() == resp2.json()  # Should be identical

    # PUT alias
    data = {
        "city": "Aliasville",
        "available_from": "2027-01-01",
        "available_to": "2027-06-01",
        "budgetMin": 600,
        "budgetMax": 900,
        "interests": ["music", "chess"],
        "hidden": False
    }
    r1 = client.put("/seekers/me/profile", json=data)
    r2 = client.put("/profiles/me", json=data)
    print("PUT /seekers/me/profile:", r1.json())
    print("PUT /profiles/me:", r2.json())
    assert r1.json() == r2.json()

def test_patch_hide_validation():
    # Hide with valid data
    resp = client.patch("/profiles/hide", json={"hidden": True})
    print("PATCH /profiles/hide (hidden True):", resp.json())
    assert_status(resp, 200)
    data = resp.json()
    assert "hidden" in data and data["hidden"] is True

    # Try to patch hide without boolean
    resp = client.patch("/profiles/hide", json={"hidden": None})
    print("PATCH /profiles/hide (hidden None):", resp.text)
    assert_status(resp, 422)

def test_missing_required_fields():
    # No city, budgets, or date fields
    resp = client.put("/seekers/me/profile", json={})
    print("PUT /seekers/me/profile (missing required fields):", resp.json())
    assert_status(resp, 200)  # Should succeed with all nullable

def test_budget_negative():
    resp = client.put("/seekers/me/profile", json={
        "budgetMin": -10, "budgetMax": 50
    })
    print("PUT /seekers/me/profile (negative budgetMin):", resp.json())
    data = resp.json()
    assert data["budgetMin"] == "0"  # should be clamped to zero

def test_budget_max_none():
    # Only min budget set, max not provided
    resp = client.put("/seekers/me/profile", json={"budgetMin": 400})
    print("PUT /seekers/me/profile (budgetMax None):", resp.json())
    assert_status(resp, 200)

def test_interests_serialization():
    resp = client.put("/seekers/me/profile", json={"interests": ["Dog", "Cat", "Dog"]})
    print("PUT /seekers/me/profile (interests serialization):", resp.json())
    data = resp.json()
    assert set(data["interests"]) == {"Dog", "Cat"}

def test_toggle_hidden_alias_and_get_profile_hidden():
    # Set hidden True again; test both PATCH endpoints if supported
    resp = client.patch("/profiles/hide", json={"hidden": True})
    print("PATCH /profiles/hide (hidden True):", resp.json())
    assert_status(resp, 200)
    # Confirm hidden reflected in GET alias
    profile = client.get("/profiles/me")
    print("GET /profiles/me (after hidden True):", profile.json())
    assert profile.json().get("hidden") is True
    # Unhide for cleanup
    client.patch("/profiles/hide", json={"hidden": False})

def test_swipe_queue_hidden_filtered():
    # This one requires implementation of host swipe queue endpoint!
    # Here’s an example assuming /host/swipe/queue returns seekers
    client.patch("/profiles/hide", json={"hidden": True})
    swipe_resp = client.get("/host/swipe/queue")
    print("GET /host/swipe/queue:", swipe_resp.json())
    if swipe_resp.status_code == 200:
        seekers = swipe_resp.json().get("seekers", [])
        # Should not contain any seekers with hidden == True
        for seeker in seekers:
            assert not seeker.get("hidden")
    client.patch("/profiles/hide", json={"hidden": False})

# Add these calls to your main or pytest runner as needed
if __name__ == "__main__":
    test_profile_alias_get_put()
    test_patch_hide_validation()
    test_missing_required_fields()
    test_budget_negative()
    test_budget_max_none()
    test_interests_serialization()
    test_toggle_hidden_alias_and_get_profile_hidden()
    # test_swipe_queue_hidden_filtered()  # Uncomment if swipe queue endpoint exists
    print("All edge case tests completed.")

def pretty_print(resp):
    print("Status:", resp.status_code)
    try:
        print(resp.json())
    except Exception:
        print(resp.text)

def test_create_valid():
    resp = client.put(
        "/seekers/me/profile",
        json={
            "city": "Minneapolis",
            "available_from": "2026-01-01",
            "available_to": "2026-05-31",
            "budgetMin": 400,
            "budgetMax": 800,
            "interests": ["quiet", "near_campus"],
            "hidden": False
        }
    )
    print("test_create_valid:")
    pretty_print(resp)

def test_create_blank_city():
    resp = client.put(
        "/seekers/me/profile",
        json={
            "city": " ",
            "available_from": "2026-01-01",
            "available_to": "2026-05-31",
            "budgetMin": 400,
            "budgetMax": 800,
            "interests": ["quiet", "near_campus"],
            "hidden": False
        }
    )
    print("test_create_blank_city:")
    pretty_print(resp)

def test_create_invalid_date_order():
    resp = client.put(
        "/seekers/me/profile",
        json={
            "city": "Minneapolis",
            "available_from": "2026-08-01",
            "available_to": "2026-05-01",
            "budgetMin": 400,
            "budgetMax": 800,
            "interests": ["quiet", "near_campus"],
            "hidden": False
        }
    )
    print("test_create_invalid_date_order:")
    pretty_print(resp)

def test_create_invalid_budget():
    resp = client.put(
        "/seekers/me/profile",
        json={
            "city": "Minneapolis",
            "available_from": "2026-01-01",
            "available_to": "2026-05-31",
            "budgetMin": 900,
            "budgetMax": 800,
            "interests": ["quiet", "near_campus"],
            "hidden": False
        }
    )
    print("test_create_invalid_budget:")
    pretty_print(resp)

def test_patch_budget():
    resp = client.put(
        "/seekers/me/profile",
        json={
            "budgetMin": 500,
            "budgetMax": 700
        }
    )
    print("test_patch_budget:")
    pretty_print(resp)

def test_toggle_hidden():
    resp = client.patch(
        "/profiles/hide",
        json={"hidden": True}
    )
    print("test_toggle_hidden:")
    pretty_print(resp)

def main():
    print("\n--- Create valid seeker ---")
    test_create_valid()
    print("\n--- Create with blank city ---")
    test_create_blank_city()
    print("\n--- Create with invalid date order ---")
    test_create_invalid_date_order()
    print("\n--- Create with invalid budget ---")
    test_create_invalid_budget()
    print("\n--- Patch budget ---")
    test_patch_budget()
    print("\n--- Toggle hidden ---")
    test_toggle_hidden()

if __name__ == "__main__":
    main()
