"""Shared pytest fixtures for the registration test suite.

Add reusable fixtures here as needed for Section 7 of the assignment
(e.g., a fixture providing representative student data used by multiple
tests, and a yield-based fixture that sets up and cleans up a temporary
resource).
"""

import pytest

@pytest.fixture
def default_student_scenario():
    """Provides a standard baseline scenario for a student with valid current credits and prerequisites."""
    return {
        "current_credits": 10,
        "course_credits": 3,
        "prerequisite_met": True,
        "expected": True
    }

@pytest.fixture(params=[0, 6, 12, 13, 18])
def valid_credit_loads(request):
    """Parametrized fixture providing valid total credit loads for fee calculation."""
    return request.param