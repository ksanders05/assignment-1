"""System tests (Section 5 of the assignment).

Mark every test in this file with the `system` marker. Use the provided
`system` fixture (tests/system/conftest.py); do not import anything from
src/ here -- a system test sees only HTTP and the outbox.
"""

import threading
import pytest
import requests

@pytest.mark.system
def test_system_main_success_scenario(system):
    """(a) (i) Main success scenario: student enrolls successfully, and response, schedule, seats_taken, and outbox all agree."""
    # S01 has completed CIS350 in the seed data
    response = system.enroll("S01", "SE499")
    assert response.status_code == 201
    data = response.json()
    assert data["student_id"] == "S01"
    assert data["course_code"] == "SE499"

    # Verify schedule reflects the enrollment
    schedule_response = system.get("/students/S01/schedule")
    assert schedule_response.status_code == 200
    courses = schedule_response.json()["courses"]
    assert any(c["code"] == "SE499" for c in courses)

    # Verify course seats taken updated
    course_response = system.get("/courses/SE499")
    assert course_response.status_code == 200
    assert course_response.json()["seats_taken"] == 1

    # Verify outbox notification agreement
    messages = system.outbox()
    assert len(messages) == 1
    assert messages[0]["type"] == "confirmation"
    assert messages[0]["student_id"] == "S01"
    assert messages[0]["course_code"] == "SE499"


@pytest.mark.system
def test_system_alternative_flow_missing_prerequisite(system):
    """(a) (ii) Alternative flow: student without prerequisite attempting enrollment receives rejection and proper status code."""
    # S13 has completed nothing in the seed data; SE413 requires CIS350
    response = system.enroll("S13", "SE413")
    assert response.status_code == 422

    # Verify outbox records the rejection
    messages = system.outbox()
    assert len(messages) == 1
    assert messages[0]["type"] == "rejection"
    assert messages[0]["student_id"] == "S13"
    assert messages[0]["course_code"] == "SE413"
    assert "prerequisite" in messages[0]["reason"]


@pytest.mark.system
@pytest.mark.parametrize(
    "payload,is_json",
    [
        ({"student_id": 123, "course_code": "SE499"}, True),       # Wrong type (int instead of str)
        ({"student_id": "S01"}, True),                              # Missing field
        ("not a json object string", False),                        # Non-object body
        ({"student_id": "S01", "course_code": "A" * 30}, True),     # Oversized value (>20 chars)
        ({"student_id": "S01", "course_code": "'; DROP TABLE;--"}, True) # Injection-like value
    ]
)
def test_system_robustness_invalid_bodies(system, payload, is_json):
    """(b) Robustness and security (REQ-8): invalid or hostile POST /enrollments bodies return JSON 400 and change nothing."""
    if is_json:
        response = system.http.post(f"{system.url}/enrollments", json=payload)
    else:
        response = system.http.post(f"{system.url}/enrollments", data=payload, headers={"Content-Type": "text/plain"})
    
    assert response.status_code == 400
    assert "error" in response.json()
    assert len(system.outbox()) == 0


@pytest.mark.system
@pytest.mark.parametrize(
    "method,endpoint",
    [
        ("GET", "/health"), # /health should be accessible without API key
        ("GET", "/courses/SE499"),
        ("GET", "/students/S01/schedule"),
        ("POST", "/enrollments")
    ]
)
def test_system_api_key_security(system, method, endpoint):
    """(b) Security (REQ-8): every endpoint except /health answers 401 without the API key."""
    # Create an unauthenticated session
    unauth_session = requests.Session()
    url = system.url + endpoint

    if method == "GET":
        response = unauth_session.get(url)
    elif method == "POST":
        response = unauth_session.post(url, json={"student_id": "S01", "course_code": "SE499"})

    if endpoint == "/health":
        assert response.status_code == 200
    else:
        assert response.status_code == 401


@pytest.mark.system
def test_system_concurrency_race_condition(system):
    """(c) Concurrency (REQ-2): SE499 has 3 seats. 10 eligible students request it simultaneously using threading.Barrier."""
    num_students = 10
    barrier = threading.Barrier(num_students)
    results = []

    def make_request(student_index):
        student_id = f"S{student_index:02d}"
        barrier.wait()  # Release all threads together
        response = system.enroll(student_id, "SE499")
        results.append(response.status_code)

    threads = [threading.Thread(target=make_request, args=(i,)) for i in range(1, num_students + 1)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # SE499 capacity is 3; exactly 3 should succeed (201) and 7 should conflict (409)
    assert results.count(201) == 3
    assert results.count(409) == 7

    # Verify database state seats_taken equals 3
    course_resp = system.get("/courses/SE499")
    assert course_resp.json()["seats_taken"] == 3

    # Verify outbox contains exactly 3 confirmations and 7 rejections
    messages = system.outbox()
    confirmations = [m for m in messages if m["type"] == "confirmation"]
    rejections = [m for m in messages if m["type"] == "rejection"]
    assert len(confirmations) == 3
    assert len(rejections) == 7
