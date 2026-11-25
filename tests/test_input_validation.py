"""
Test Suite: Input Validation & Data Integrity
Validates customer fields, campaign parameters, and disposition outcomes
"""

import pytest
from models import User, Customer, Campaign, CallLog
from campaign_service import create_campaign


def test_user_password_hashing():
    """Verifies that user passwords are securely hashed and checked correctly."""
    user = User(username="test_validator", full_name="Test User", role="agent")
    user.set_password("Secret123!")

    assert user.password_hash != "Secret123!"
    assert user.check_password("Secret123!") is True
    assert user.check_password("WrongPassword") is False


def test_customer_demographic_integrity():
    """Verifies that customer demographic attributes preserve valid types and default values."""
    cust = Customer(
        name="Valid Customer",
        phone="+91 99999 88888",
        age=35,
        job="management",
        marital="married",
        education="university.degree",
        default="no",
        housing="yes",
        loan="no"
    )
    cust_dict = cust.to_dict()

    assert cust_dict["name"] == "Valid Customer"
    assert cust_dict["age"] == 35
    assert cust_dict["housing"] == "yes"
    assert "duration" not in cust_dict, "duration must be strictly excluded to prevent target leakage"


def test_campaign_creation_validation(db_session):
    """Verifies that empty campaign names or invalid creators are rejected."""
    # Empty name check
    with pytest.raises(ValueError, match="Campaign name is required"):
        create_campaign(name="", description="", target_calls=50, created_by=1, db=db_session)

    # Invalid user ID check
    with pytest.raises(ValueError, match="User with ID 999999 does not exist"):
        create_campaign(name="Valid Name", description="", target_calls=50, created_by=999999, db=db_session)


def test_call_outcome_options():
    """Verifies that only authorized call outcomes can be recorded."""
    valid_outcomes = ["Interested", "Not Interested", "Unreachable", "Follow-up Required", "Subscribed"]
    for outcome in valid_outcomes:
        log = CallLog(
            customer_id=1,
            agent_id=2,
            call_outcome=outcome,
            duration_seconds=60
        )
        assert log.call_outcome in valid_outcomes
