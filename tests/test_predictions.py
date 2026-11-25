"""
Test Suite: Predictions & Prioritization
Verifies ML pipeline scoring, priority mapping, and leakage prevention
"""

import pytest
from ml_engine import predict_single, batch_score_customers, FEATURES


def test_no_target_leakage_in_features():
    """Confirms that duration is strictly excluded from all model feature definitions."""
    assert "duration" not in FEATURES, "duration causes target leakage and must never be in FEATURES"


def test_predict_single_output_format():
    """Verifies that predict_single returns valid probabilities, priorities, and outcomes."""
    customer = {
        "age": 28,
        "job": "student",
        "marital": "single",
        "education": "university.degree",
        "default": "no",
        "housing": "no",
        "loan": "no",
        "contact": "cellular",
        "month": "apr",
        "day_of_week": "thu",
        "campaign": 1,
        "pdays": 3,
        "previous": 2,
        "poutcome": "success",
        "emp_var_rate": -1.8,
        "cons_price_idx": 93.075,
        "cons_conf_idx": -47.1,
        "euribor3m": 1.405,
        "nr_employed": 5099.1
    }
    result = predict_single(customer)

    assert "subscription_probability" in result
    assert 0.0 <= result["subscription_probability"] <= 1.0
    assert result["priority"] in ["High", "Medium", "Low"]
    assert result["predicted_outcome"] in [0, 1]
    assert result["selected_model"] in ["Original XGBoost", "Missingness-Aware V2"]


def test_batch_scoring_sorting_order():
    """Verifies that batch scoring returns records ordered by priority and probability descending."""
    customers = [
        {
            "id": 1,
            "age": 56,
            "job": "housemaid",
            "marital": "married",
            "education": "basic.4y",
            "default": "no",
            "housing": "no",
            "loan": "no",
            "pdays": 999,
            "previous": 0,
            "poutcome": "nonexistent"
        },
        {
            "id": 2,
            "age": 25,
            "job": "student",
            "marital": "single",
            "education": "university.degree",
            "default": "no",
            "housing": "no",
            "loan": "no",
            "pdays": 6,
            "previous": 2,
            "poutcome": "success",
            "emp_var_rate": -1.7,
            "euribor3m": 0.899
        }
    ]
    scored = batch_score_customers(customers, campaign_id=1)

    assert len(scored) == 2
    # The high propensity customer (student, previous success) should be ranked higher
    assert scored[0]["subscription_probability"] >= scored[1]["subscription_probability"]
    assert scored[0]["customer_id"] == 2
