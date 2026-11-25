"""
Test Suite: Edge Cases & Boundary Handling
Verifies robustness against extreme demographic inputs, unknown categories, and sparse records
"""

import pytest
from ml_engine import predict_single, prepare_customer_data
from assignment_service import preview_workload_distribution


def test_edge_case_elderly_customer():
    """Verifies that senior retiree profiles are scored gracefully."""
    senior_customer = {
        "age": 92,
        "job": "retired",
        "marital": "married",
        "education": "basic.4y",
        "default": "no",
        "housing": "no",
        "loan": "no"
    }
    result = predict_single(senior_customer)

    assert "subscription_probability" in result
    assert 0.0 <= result["subscription_probability"] <= 1.0


def test_edge_case_all_unknown_demographics():
    """Verifies handling of 'unknown' values present in benchmark datasets."""
    unknown_customer = {
        "age": 40,
        "job": "unknown",
        "marital": "unknown",
        "education": "unknown",
        "default": "unknown",
        "housing": "unknown",
        "loan": "unknown"
    }
    result = predict_single(unknown_customer)

    assert result["status"] if "status" in result else "subscription_probability" in result


def test_edge_case_high_campaign_contacts():
    """Verifies handling of heavily contacted leads (high campaign repetition)."""
    repeat_customer = {
        "age": 45,
        "job": "services",
        "marital": "married",
        "education": "high.school",
        "default": "no",
        "housing": "yes",
        "loan": "yes",
        "campaign": 56,
        "previous": 12,
        "pdays": 999
    }
    result = predict_single(repeat_customer)

    assert 0.0 <= result["subscription_probability"] <= 1.0


def test_workload_preview_nonexistent_campaign(db_session):
    """Verifies that requesting workload preview for an invalid campaign raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        preview_workload_distribution(campaign_id=999999, db=db_session)
