"""
Test Suite: Missing Values & Adaptive Model Routing
Verifies that the prediction router switches between Original and V2 models
"""

import pandas as pd
import numpy as np
from ml_engine import prepare_customer_data, choose_model, OPTIONAL_FEATURES


def test_complete_data_routes_to_original_model():
    """Verifies that complete records route to Original XGBoost with Complete threshold."""
    complete_record = {
        "age": 45,
        "job": "management",
        "marital": "married",
        "education": "university.degree",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": "cellular",
        "month": "may",
        "day_of_week": "mon",
        "campaign": 1,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.1,
        "cons_price_idx": 93.994,
        "cons_conf_idx": -36.4,
        "euribor3m": 4.857,
        "nr_employed": 5191.0
    }
    df = prepare_customer_data(complete_record)
    selection = choose_model(df.iloc[0])

    assert selection["model_name"] == "Original XGBoost"
    assert selection["scenario"] == "Complete"
    assert selection["missing_count"] == 0
    assert selection["threshold"] == 0.73046


def test_low_missingness_routes_to_original_model():
    """Verifies that 1 missing optional attribute routes to Original XGBoost (10% missing)."""
    record = {
        "age": 45,
        "job": "admin.",
        "marital": "single",
        "education": "university.degree",
        "default": "no",
        "housing": "yes",
        "loan": "no",
        "contact": None,  # 1 missing
        "month": "may",
        "day_of_week": "mon",
        "campaign": 1,
        "pdays": 999,
        "previous": 0,
        "poutcome": "nonexistent",
        "emp_var_rate": 1.1,
        "cons_price_idx": 93.994,
        "cons_conf_idx": -36.4,
        "euribor3m": 4.857,
        "nr_employed": 5191.0
    }
    df = prepare_customer_data(record)
    selection = choose_model(df.iloc[0])

    assert selection["model_name"] == "Original XGBoost"
    assert selection["scenario"] == "10% missing"
    assert selection["missing_count"] == 1
    assert selection["threshold"] == 0.55532


def test_high_missingness_routes_to_v2_model():
    """Verifies that >= 4 missing optional attributes dynamically route to Missingness-Aware V2."""
    record = {
        "age": 30,
        "job": "technician",
        "marital": "single",
        "education": "professional.course",
        "default": "no",
        "housing": "no",
        "loan": "no",
        "contact": None,
        "month": None,
        "day_of_week": None,
        "campaign": None,
        "pdays": None,
        "previous": None,
        "poutcome": None,
        "emp_var_rate": None,
        "cons_price_idx": None,
        "cons_conf_idx": None,
        "euribor3m": None,
        "nr_employed": None
    }
    df = prepare_customer_data(record)
    selection = choose_model(df.iloc[0])

    assert selection["model_name"] == "Missingness-Aware V2"
    assert selection["scenario"] == "100% missing"
    assert selection["threshold"] == 0.49670
