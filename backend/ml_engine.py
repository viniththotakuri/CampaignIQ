"""
ML Intelligence Engine for CampaignIQ
PS-8 Banking Call Center Intelligence System

Integrates your friend's trained XGBoost models and preprocessors directly
from model_loader.py without modifying the trained .pkl artifacts.

Features:
- Single & batch customer data preparation (mapping DB fields to training schema)
- Leakage prevention (duration strictly omitted)
- Feature engineering (was_previously_contacted, had_previous_campaign)
- Missingness-aware model selection (Original XGBoost vs Missingness-Aware V2)
- Probability scoring and priority categorization (High, Medium, Low)
"""

import pandas as pd
import numpy as np

pd.set_option("future.no_silent_downcasting", True)

from model_loader import (
    original_model,
    original_preprocessor,
    v2_model,
    v2_preprocessor
)

# --------------------------------------------------
# FEATURE DEFINITIONS (Exact match to model training)
# --------------------------------------------------

OPTIONAL_FEATURES = [
    "contact", "month", "day_of_week", "campaign",
    "pdays", "previous", "poutcome",
    "emp.var.rate", "cons.price.idx", "cons.conf.idx",
    "euribor3m", "nr.employed",
    "was_previously_contacted",
    "had_previous_campaign"
]

FEATURES = [
    "age", "job", "marital", "education", "default",
    "housing", "loan", "contact", "month", "day_of_week",
    "campaign", "pdays", "previous", "poutcome",
    "emp.var.rate", "cons.price.idx", "cons.conf.idx",
    "euribor3m", "nr.employed",
    "was_previously_contacted",
    "had_previous_campaign"
]

NUMERIC_FEATURES = [
    "age", "campaign", "pdays", "previous",
    "emp.var.rate", "cons.price.idx", "cons.conf.idx",
    "euribor3m", "nr.employed",
    "was_previously_contacted",
    "had_previous_campaign"
]

VALIDATION_THRESHOLDS = {
    "Original XGBoost": {
        "Complete": 0.73046,
        "10% missing": 0.55532,
        "25% missing": 0.55385
    },
    "Missingness-Aware V2": {
        "40% missing": 0.66003,
        "60% missing": 0.58101,
        "100% missing": 0.49670
    }
}


def prepare_customer_data(raw_records):
    """
    Transforms raw customer dictionary or list of dictionaries into a DataFrame
    ready for feature extraction and model inference.
    """
    if isinstance(raw_records, dict):
        raw_records = [raw_records]

    df = pd.DataFrame(raw_records)

    # Rename database/API fields to match model training dataset column names
    rename_mapping = {
        "emp_var_rate": "emp.var.rate",
        "cons_price_idx": "cons.price.idx",
        "cons_conf_idx": "cons.conf.idx",
        "nr_employed": "nr.employed"
    }
    df = df.rename(columns=rename_mapping)

    # Convert None and empty strings to NaN
    df = df.replace({None: np.nan, "": np.nan}).infer_objects(copy=False)

    # Ensure required columns exist
    for col in FEATURES:
        if col not in df.columns:
            df[col] = np.nan

    # Feature engineering: was_previously_contacted
    if "pdays" in df.columns:
        df["was_previously_contacted"] = np.where(
            df["pdays"].isna(),
            np.nan,
            (df["pdays"] != 999).astype(float)
        )
    else:
        df["was_previously_contacted"] = np.nan

    # Feature engineering: had_previous_campaign
    if "previous" in df.columns:
        df["had_previous_campaign"] = np.where(
            df["previous"].isna(),
            np.nan,
            (df["previous"] > 0).astype(float)
        )
    else:
        df["had_previous_campaign"] = np.nan

    # Strict feature ordering matching training
    df = df[FEATURES].copy()

    # Coerce numeric fields
    for col in NUMERIC_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def choose_model(row_series):
    """
    Selects the best model and validation threshold for a single record
    based on missing optional fields count.
    """
    missing_count = int(row_series[OPTIONAL_FEATURES].isna().sum())
    total_optional = len(OPTIONAL_FEATURES)
    missing_pct = (missing_count / total_optional) * 100.0

    if missing_count <= 3:
        model = original_model
        preprocessor = original_preprocessor
        model_name = "Original XGBoost"

        if missing_count == 0:
            scenario = "Complete"
            threshold = VALIDATION_THRESHOLDS[model_name]["Complete"]
        elif missing_count == 1:
            scenario = "10% missing"
            threshold = VALIDATION_THRESHOLDS[model_name]["10% missing"]
        else:
            scenario = "25% missing"
            threshold = VALIDATION_THRESHOLDS[model_name]["25% missing"]
    else:
        model = v2_model
        preprocessor = v2_preprocessor
        model_name = "Missingness-Aware V2"

        if missing_count <= 7:
            scenario = "40% missing"
            threshold = VALIDATION_THRESHOLDS[model_name]["40% missing"]
        elif missing_count <= 11:
            scenario = "60% missing"
            threshold = VALIDATION_THRESHOLDS[model_name]["60% missing"]
        else:
            scenario = "100% missing"
            threshold = VALIDATION_THRESHOLDS[model_name]["100% missing"]

    return {
        "model": model,
        "preprocessor": preprocessor,
        "model_name": model_name,
        "scenario": scenario,
        "threshold": threshold,
        "missing_count": missing_count,
        "missing_percentage": round(missing_pct, 2)
    }


def determine_priority(probability, threshold):
    """
    Categorizes customers into operational priority tiers for call center queues.
    - High: High probability of conversion (>= 0.50 or >= validation threshold)
    - Medium: Moderate potential (>= 0.20 and < 0.50)
    - Low: Low propensity (< 0.20)
    """
    if probability >= 0.50 or probability >= threshold:
        return "High"
    elif probability >= 0.20:
        return "Medium"
    else:
        return "Low"


def predict_single(customer_dict):
    """
    Runs end-to-end prediction for a single customer dictionary.
    Returns scoring dictionary with probability, priority, and metadata.
    """
    data = prepare_customer_data(customer_dict)
    selection = choose_model(data.iloc[0])

    model = selection["model"]
    preprocessor = selection["preprocessor"]

    processed = preprocessor.transform(data)
    probability = float(model.predict_proba(processed)[0][1])

    threshold = selection["threshold"]
    prediction = int(probability >= threshold)
    priority = determine_priority(probability, threshold)

    return {
        "selected_model": selection["model_name"],
        "scenario": selection["scenario"],
        "missing_features_count": selection["missing_count"],
        "missing_percentage": selection["missing_percentage"],
        "subscription_probability": round(probability, 4),
        "subscription_percentage": round(probability * 100, 2),
        "predicted_outcome": prediction,
        "priority": priority,
        "validation_threshold": threshold
    }


def batch_score_customers(customer_records, campaign_id=None):
    """
    Batches scoring across multiple customer database records.
    Returns a list of prediction dictionaries ranked by priority and probability.
    """
    if not customer_records:
        return []

    # Format customer records into dicts
    records_data = []
    customer_ids = []
    for c in customer_records:
        c_dict = c.to_dict() if hasattr(c, "to_dict") else dict(c)
        customer_ids.append(c_dict["id"])
        records_data.append(c_dict)

    df_prepared = prepare_customer_data(records_data)
    results = []

    # Score each row using the adaptive router
    for idx, row in df_prepared.iterrows():
        cust_id = customer_ids[idx]
        try:
            selection = choose_model(row)
            model = selection["model"]
            preprocessor = selection["preprocessor"]

            # Single row DataFrame for transformation
            row_df = pd.DataFrame([row])
            processed = preprocessor.transform(row_df)
            prob = float(model.predict_proba(processed)[0][1])
            threshold = selection["threshold"]
            outcome = int(prob >= threshold)
            priority = determine_priority(prob, threshold)

            results.append({
                "customer_id": cust_id,
                "campaign_id": campaign_id,
                "model_used": selection["model_name"],
                "scenario": selection["scenario"],
                "subscription_probability": round(prob, 4),
                "priority": priority,
                "predicted_outcome": outcome,
                "missing_features_count": selection["missing_count"]
            })
        except Exception as err:
            import logging
            logging.getLogger(__name__).warning(f"Failed to score customer ID {cust_id}: {err}")
            continue

    # Sort results by probability descending (High priority calling queue)
    priority_order = {"High": 1, "Medium": 2, "Low": 3}
    results.sort(
        key=lambda r: (priority_order.get(r["priority"], 99), -r["subscription_probability"])
    )

    return results
