"""Integration tests (Section 4 of the assignment).

Mark every test in this file with the `integration` marker, e.g.

    pytestmark = pytest.mark.integration

Modules are importable directly (see pyproject.toml), e.g.

    import db
    from repository import RegistrationRepository
    from service import RegistrationService
    from errors import CourseFull, AlreadyEnrolled, NotEligible
"""

import pytest
import sqlite3
from src.errors import CourseFull, AlreadyEnrolled

@pytest.mark.integration
def test_repo_take_seat_capacity_boundary(db_conn, sample_data, repo):
    """(i) take_seat() at capacity boundary: last seat succeeds; one more is refused[cite: 4]."""
    # SE499 has capacity 2
    assert repo.take_seat("SE499") is True
    assert repo.take_seat("SE499") is True
    assert repo.take_seat("SE499") is False


@pytest.mark.integration
def test_repo_duplicate_enrollment_rejected(db_conn, sample_data, repo):
    """(ii) Duplicate enrollment is rejected by the database[cite: 4]."""
    repo.add_enrollment("S01", "SE499")
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_enrollment("S01", "SE499")


@pytest.mark.integration
def test_repo_current_credits_count(db_conn, sample_data, repo):
    """(iii) current_credits() counts only that student's courses, and is 0 for a student with none[cite: 4]."""
    # S01 has no active enrollments initially
    assert repo.current_credits("S01") == 0
    repo.add_enrollment("S01", "SE499")
    assert repo.current_credits("S01") == 3


@pytest.mark.integration
def test_repo_transaction_atomicity(db_conn, sample_data, repo):
    """(iv) A transaction that fails part-way leaves neither the seat nor the enrollment behind[cite: 4]."""
    initial_seats = repo.get_course("SE499")["seats_taken"]
    with pytest.raises(Exception):
        with db_conn:
            repo.take_seat("SE499")
            # Force integrity error by duplicating enrollment
            repo.add_enrollment("S01", "SE499")
            repo.add_enrollment("S01", "SE499")
    
    assert repo.get_course("SE499")["seats_taken"] == initial_seats
    assert repo.current_credits("S01") == 0


@pytest.mark.integration
def test_service_successful_enrollment(sample_data, service, fake_notifier, repo):
    """Service + repository + notifier: successful enrollment (state & outbox check)[cite: 4]."""
    result = service.enroll("S01", "SE499")
    assert result["enrolled"] if "enrolled" in result else result["student_id"] == "S01"
    assert repo.get_course("SE499")["seats_taken"] == 1
    assert any(msg[0] == "confirmation" and msg[1] == "S01" for msg in fake_notifier.outbox)


@pytest.mark.integration
def test_service_course_full(sample_data, service, fake_notifier, repo):
    """Service + repository + notifier: full course rejection[cite: 4]."""
    service.enroll("S01", "SE499")
    service.enroll("S02", "SE499")
    with pytest.raises(CourseFull):
        # Try enrolling a third student (we can add S03 temporarily)
        repo.add_student("S03", "Charlie")
        repo.add_completed("S03", "CIS350")
        service.enroll("S03", "SE499")
    assert any(msg[0] == "rejection" and "course is full" in msg[3] for msg in fake_notifier.outbox)


@pytest.mark.integration
def test_service_duplicate_enrollment(sample_data, service, fake_notifier):
    """Service + repository + notifier: duplicate enrollment error[cite: 4]."""
    service.enroll("S01", "SE499")
    with pytest.raises(AlreadyEnrolled):
        service.enroll("S01", "SE499")


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="REQ-6 defect: repository remove_enrollment deletes by course_code instead of student_id and course_code.")
def test_known_defect_withdrawing(sample_data, service, repo):
    """(d) Integration test exposing the REQ-6 course withdrawal defect[cite: 4]."""
    service.enroll("S01", "SE499")
    service.enroll("S02", "SE499")
    # Withdrawing S01 incorrectly deletes all enrollments for SE499 due to repository bug
    service.withdraw("S01", "SE499")
    # S02 should still be enrolled, but the bug removes S02 as well
    schedule_s02 = service.schedule("S02")
    assert any(c["code"] == "SE499" for c in schedule_s02["courses"])