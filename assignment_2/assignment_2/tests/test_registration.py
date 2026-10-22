"""Test suite for src/registration.py.

This file is intentionally left for you to implement. See the assignment
handout for the required test-design work:

  - Section 4: Equivalence partitioning
  - Section 5: Boundary-value analysis
  - Section 6: Positive and negative testing with pytest
  - Section 7: Parametrization and fixtures
  - Section 8: Organize and demonstrate the test suite (markers, README)

`registration` is importable directly (see pyproject.toml's `pythonpath`
setting), e.g.:

    from registration import can_register, calculate_registration_fee
"""

import pytest
from src.registration import can_register, calculate_registration_fee
from unittest.mock import Mock
from src.registration import summarize_batch_registrations, enroll_student

# --- Tests for can_regiser (Equivalence Partitioning & Boundary Value Analysis) ---

@pytest.mark.parametrize(
    "current_credits, course_credits, prerequisite_met, expected",
    [
        # Boundary values for current_credits [0, 15]
        (0, 3, True, True),     # Minimum valid current credits
        (15, 3, True, True),    # Maximum valid current credits
        (-1, 3, True, False),   # Below lower boundary for current credits
        (16, 3, True, False),   # Above upper boundary for current credits

        # Boundary values for course_credits [1, 4]
        (10, 1, True, True),    # Minimum valid course credits
        (10, 4, True, True),    # Maximum valid course credits
        (10, 0, True, False),   # Below lower boundary for course credits
        (10, 5, True, False),   # Above upper boundary for course credits

        # Boundary values for total resulting credits (must not exceed 18)
        (14, 4, True, True),    # Exactly 18 total credits (upper bound)
        (15, 4, True, False),   # Results in 19 credits (exceeds limit)

        # Prerequisite validation (Positive/Negative)
        (10, 3, True, True),    # Prerequisite met
        (10, 3, False, False),  # Prerequisite not met
    ]
)
def test_can_register(current_credits, course_credits, prerequisite_met, expected):
    """Verify course registration rules across valid and invalid boundary partitions."""
    assert can_register(current_credits, course_credits, prerequisite_met) == expected


# --- Tests for calculate_registration_fee (Fee Structure & Error Handling) ---

@pytest.mark.parametrize(
    "total_credits, expected_fee",
    [
        (0, 0.0),       # Lower boundary: 0 credits
        (1, 100.0),     # Lower tier standard rate
        (12, 1200.0),   # Upper boundary of first tier (12 * $100)
        (13, 1275.0),   # Lower boundary of discounted tier (12 * $100 + 1 * $75)
        (18, 1650.0),   # Upper boundary of total allowed credits (12 * $100 + 6 * $75)
    ]
)
def test_calculate_registration_fee_valid(total_credits, expected_fee):
    """Verify correct fee calculations for valid credit loads within [0, 18]."""
    assert calculate_registration_fee(total_credits) == pytest.approx(expected_fee)


@pytest.mark.parametrize(
    "invalid_credits",
    [
        -1,     # Just below minimum valid boundary
        19,     # Just above maximum valid boundary
        100,    # Out-of-bounds large value
    ]
)
def test_calculate_registration_fee_raises_value_error(invalid_credits):
    """Ensure ValueError is raised when total_credits falls outside the [0, 18] range."""
    with pytest.raises(ValueError):
        calculate_registration_fee(invalid_credits)


def test_fee_with_fixture(valid_credit_loads):
    """Demonstrate the use of a fixture to test credit loads."""
    # This test ensures no unexpected exceptions are raised for valid loads provided by the fixture
    fee = calculate_registration_fee(valid_credit_loads)
    assert isinstance(fee, float)
    assert fee >= 0.0
    
def test_summarize_batch_registrations_empty():
    """Ensure an empty batch returns zero count and zero fees."""
    count, fees = summarize_batch_registrations([])
    assert count == 0
    assert fees == 0.0


def test_summarize_batch_registrations_mixed():
    """Verify that batch processing correctly handles a mix of approved and rejected requests."""
    requests = [
        (5, 3, True),   # Approved: 8 credits -> 8 * 100.0 = 800.0
        (15, 4, True),  # Rejected: results in 19 credits (exceeds limit)
        (0, 3, True),   # Approved: 3 credits -> 3 * 100.0 = 300.0
        (10, 3, False), # Rejected: prerequisite not met
    ]
    
    count, fees = summarize_batch_registrations(requests)
    assert count == 2
    assert fees == pytest.approx(1100.0)


# --- Tests for enroll_student ---

def test_enroll_student_success():
    """Ensure successful enrollment computes the fee, triggers confirmation, and returns True."""
    mock_notifier = Mock()
    
    success = enroll_student(5, 3, True, mock_notifier)
    
    assert success is True
    mock_notifier.send_confirmation.assert_called_once_with(800.0)
    mock_notifier.send_rejection.assert_not_called()


def test_enroll_student_failure():
    """Ensure failed enrollment triggers rejection notification and returns False."""
    mock_notifier = Mock()
    
    # Prerequisite not met should cause failure
    success = enroll_student(5, 3, False, mock_notifier)
    
    assert success is False
    mock_notifier.send_rejection.assert_called_once()
    mock_notifier.send_confirmation.assert_not_called()
    
def test_summarize_batch_registrations_loop_carried():
    """Verify the loop-carried DU-pair by processing at least two approved requests."""
    # Both requests are valid, ensuring the loop runs twice and updates total_fees twice
    requests = [
        (5, 3, True),  # Approved (8 credits -> $800.0)
        (0, 3, True),  # Approved (3 credits -> $300.0)
    ]
    
    count, fees = summarize_batch_registrations(requests)
    assert count == 2
    assert fees == pytest.approx(1100.0)
    
#
    
def test_enroll_student_positive_allowed():
    """Positive test for the allowed case using state and behavior verification[cite: 3]."""
    mock_notifier = Mock()
    
    # State verification: assert return value is True
    success = enroll_student(5, 3, True, mock_notifier)
    assert success is True
    
    # Behavior verification: assert send_confirmation was called with correct fee, rejection was not
    mock_notifier.send_confirmation.assert_called_once_with(800.0)
    mock_notifier.send_rejection.assert_not_called()


def test_enroll_student_negative_rejected():
    """Negative test for the rejected case using state and behavior verification[cite: 3]."""
    mock_notifier = Mock()
    
    # State verification: assert return value is False (prerequisite not met)
    success = enroll_student(5, 3, False, mock_notifier)
    assert success is False
    
    # Behavior verification: assert send_rejection was called once with no args, confirmation was not
    mock_notifier.send_rejection.assert_called_once()
    mock_notifier.send_confirmation.assert_not_called()