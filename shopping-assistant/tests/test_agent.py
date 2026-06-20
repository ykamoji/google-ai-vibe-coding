import pytest
from unittest.mock import patch

# Mock google.auth.default to prevent credentials error during test collection
patcher = patch("google.auth.default", return_value=(None, "mock-project-id"))
patcher.start()

from app.agent import redeem_discount_code, REDEEMED_CODES

@pytest.fixture(autouse=True)
def reset_redeemed_codes():
    """Fixture to reset the REDEEMED_CODES state before each test."""
    # Store original state if we wanted, but since it's tests we can just clear them
    REDEEMED_CODES["WELCOME50"].clear()
    REDEEMED_CODES["SUMMER20"].clear()
    yield

def test_redeem_discount_code_success():
    """Test successful redemption of a valid discount code."""
    result = redeem_discount_code("WELCOME50", "user_123")
    assert "Success" in result
    assert "user_123" in result
    assert "user_123" in REDEEMED_CODES["WELCOME50"]

def test_redeem_discount_code_invalid_code():
    """Test that an invalid discount code is rejected."""
    result = redeem_discount_code("HACKER99", "user_123")
    assert "Error" in result
    assert "invalid" in result

def test_redeem_discount_code_already_redeemed():
    """Test idempotency: a user cannot redeem the same code twice (Replay Attack)."""
    # First redemption
    result1 = redeem_discount_code("SUMMER20", "user_456")
    assert "Success" in result1

    # Second redemption attempt
    result2 = redeem_discount_code("SUMMER20", "user_456")
    assert "Error" in result2
    assert "already redeemed" in result2

def test_redeem_discount_code_case_insensitivity():
    """Test that discount codes are processed case-insensitively."""
    result = redeem_discount_code("welcome50", "user_789")
    assert "Success" in result
    assert "user_789" in REDEEMED_CODES["WELCOME50"]
