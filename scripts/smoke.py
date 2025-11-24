from __future__ import annotations

import json
import shlex
import subprocess

# Run file with make smoke, add new tests to the tests list in main()

BASE_URL = "http://127.0.0.1:8000"
SEEKER_ID = "user-1"
HOST_ID = "user-10"

# A listing ID that is assumed to exist from seed data
EXAMPLE_LISTING_ID = "listing-1"


def run_test(name: str, command: str, expect_fail: bool = False):
    """Runs a shell command and prints the results."""
    print(f"▶️  Running test: {name}")
    print(f"   $ {command}")

    # Use shlex.split for robust command parsing
    args = shlex.split(command)
    process = subprocess.run(args, capture_output=True, text=True, check=False)

    success = (process.returncode != 0) if expect_fail else (process.returncode == 0)

    if success:
        print("✅ PASSED\n")
    else:
        print(f"❌ FAILED (Exit code: {process.returncode})")
        if process.stdout:
            print("   --- STDOUT ---")
            print(process.stdout)
        if process.stderr:
            print("   --- STDERR ---")
            print(process.stderr)
        print("")

    return success


def main():
    """Executes all API smoke tests."""
    print("🚀 Starting API Smoke Tests...")
    print("-" * 30)

    # Define all tests
    # Each tuple is (test_name, command_string, expect_fail_flag)
    tests = [
        # Health Check
        ("Health Check", f"curl -s -f {BASE_URL}/healthz", False),
        # Seeker Profile
        (
            "Get Seeker Profile",
            f'curl -s -f {BASE_URL}/seekers/me/profile -H "X-Debug-User-Id: {SEEKER_ID}"',
            False,
        ),
        (
            "Update Seeker Profile",
            f"""curl -s -f -X PUT {BASE_URL}/seekers/me/profile \
                -H "X-Debug-User-Id: {SEEKER_ID}" \
                -H "Content-Type: application/json" \
                -d '{json.dumps({"bio": "New test bio", "gender": "non-binary"})}'""",
            False,
        ),
        (
            "Hide Seeker Profile",
            f'curl -s -f -X PATCH {BASE_URL}/profiles/hide -H "X-Debug-User-Id: {SEEKER_ID}" -H "Content-Type: application/json" -d \'{{"hidden": true}}\'',
            False,
        ),
        # Host Listing
        (
            "Get Host Listing",
            f'curl -s -f {BASE_URL}/hosts/me/listing -H "X-Debug-User-Id: {HOST_ID}"',
            False,
        ),
        (
            "Update Host Listing",
            f"""curl -s -f -X PUT {BASE_URL}/hosts/me/listing \
                -H "X-Debug-User-Id: {HOST_ID}" \
                -H "Content-Type: application/json" \
                -d '{json.dumps({"title": "New Test Title", "description": "Updated via test."})}'""",
            False,
        ),
        (
            "Publish Host Listing",
            f'curl -s -f -X PATCH {BASE_URL}/listings/{EXAMPLE_LISTING_ID}/publish -H "X-Debug-User-Id: {HOST_ID}"',
            False,
        ),
        # Swipe Flows
        (
            "Get Seeker Swipe Queue",
            f'curl -s -f {BASE_URL}/swipe/queue/seeker -H "X-Debug-User-Id: {SEEKER_ID}"',
            False,
        ),
        (
            "Get Host Swipe Queue",
            f'curl -s -f {BASE_URL}/swipe/queue/host -H "X-Debug-User-Id: {HOST_ID}"',
            False,
        ),
        # Matches
        (
            "Get Matches",
            f'curl -s -f {BASE_URL}/matches -H "X-Debug-User-Id: {SEEKER_ID}"',
            False,
        ),
        # Problem Details Examples (expected failures)
        (
            "404 on Missing Host Context",
            f'curl -s -f {BASE_URL}/swipe/queue/host -H "X-Debug-User-Id: user-999"',
            True,
        ),
        (
            "422 on Invalid Swipe Decision",
            f"""curl -s -f -X POST {BASE_URL}/swipe/swipes \
                -H "X-Debug-User-Id: {SEEKER_ID}" \
                -H "Content-Type: application/json" \
                -d '{json.dumps({"targetId": EXAMPLE_LISTING_ID, "decision": "maybe"})}'""",
            True,
        ),
    ]

    results = [run_test(*test) for test in tests]

    print("-" * 30)
    if all(results):
        print(f"🎉 All {len(results)} tests passed!")
        exit(0)
    else:
        failed_count = results.count(False)
        print(f"🔥 {failed_count} of {len(results)} tests failed.")
        exit(1)


if __name__ == "__main__":
    main()
