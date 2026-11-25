
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
import pandas as pd
import numpy as np

from model_loader import (
    original_model,
    original_preprocessor,
    v2_model,
    v2_preprocessor
)


# --------------------------------------------------
# 1. FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="CampaignIQ API",
    description="AI-powered Bank Telemarketing Prediction API",
    version="2.1.0"
)


# --------------------------------------------------
# 2. CUSTOMER INPUT MODEL
# --------------------------------------------------

class Customer(BaseModel):

    # Required customer information
    age: int
    job: str
    marital: str
    education: str
    default: str
    housing: str
    loan: str

    # Optional campaign information
    contact: str | None = None
    month: str | None = None
    day_of_week: str | None = None
    campaign: int | None = None
    pdays: int | None = None
    previous: int | None = None
    poutcome: str | None = None

    # Optional economic indicators
    emp_var_rate: float | None = None
    cons_price_idx: float | None = None
    cons_conf_idx: float | None = None
    euribor3m: float | None = None
    nr_employed: float | None = None

    @field_validator("age")
    @classmethod
    def validate_age(cls, value):
        if value < 17 or value > 100:
            raise ValueError(
                "Enter a valid customer age between 17 and 100."
            )
        return value

    @field_validator(
        "job", "marital", "education",
        "default", "housing", "loan"
    )
    @classmethod
    def validate_customer_fields(cls, value):

        if not value or value.strip().lower() in [
            "string", "none", "null", "undefined"
        ]:
            raise ValueError(
                "Valid customer information is required. "
                "Placeholder values are not accepted."
            )

        return value.strip()

    @field_validator(
        "contact", "month", "day_of_week", "poutcome"
    )
    @classmethod
    def validate_optional_text(cls, value):

        if value is not None and value.strip().lower() in [
            "string", "none", "null", "undefined"
        ]:
            raise ValueError(
                "Use null for missing information instead "
                "of placeholder values."
            )

        return value.strip() if value is not None else None


# --------------------------------------------------
# 3. FEATURE DEFINITIONS
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


# --------------------------------------------------
# 4. VALIDATION THRESHOLDS
# --------------------------------------------------

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


# --------------------------------------------------
# 5. HOME ENDPOINT
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "Welcome to CampaignIQ API",
        "status": "running",
        "models": [
            "Original XGBoost",
            "Missingness-Aware V2"
        ]
    }


# --------------------------------------------------
# 6. HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "original_model_loaded": original_model is not None,
        "original_preprocessor_loaded": original_preprocessor is not None,
        "v2_model_loaded": v2_model is not None,
        "v2_preprocessor_loaded": v2_preprocessor is not None
    }


# --------------------------------------------------
# 7. PREPARE CUSTOMER DATA
# --------------------------------------------------

def prepare_customer_data(customer):

    data = pd.DataFrame([customer.model_dump()])

    # Rename API fields to match training dataset
    data = data.rename(columns={
        "emp_var_rate": "emp.var.rate",
        "cons_price_idx": "cons.price.idx",
        "cons_conf_idx": "cons.conf.idx",
        "nr_employed": "nr.employed"
    })

    # Convert None to NaN
    data = data.replace({None: np.nan})

    # Engineer previous contact feature
    data["was_previously_contacted"] = np.where(
        data["pdays"].isna(),
        np.nan,
        (data["pdays"] != 999).astype(float)
    )

    # Engineer previous campaign feature
    data["had_previous_campaign"] = np.where(
        data["previous"].isna(),
        np.nan,
        (data["previous"] > 0).astype(float)
    )

    # Maintain exact training feature order
    data = data[FEATURES].copy()

    # Convert numeric columns
    for column in NUMERIC_FEATURES:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

    return data


# --------------------------------------------------
# 8. MODEL SELECTION
# --------------------------------------------------

def choose_model(data):

    missing_count = int(
        data[OPTIONAL_FEATURES].isna().sum().sum()
    )

    total_optional = len(OPTIONAL_FEATURES)

    missing_percentage = (
        missing_count / total_optional
    ) * 100

    if missing_count <= 3:

        model = original_model
        preprocessor = original_preprocessor
        model_name = "Original XGBoost"

        if missing_count == 0:
            scenario = "Complete"
            threshold = VALIDATION_THRESHOLDS[
                model_name
            ]["Complete"]

        elif missing_count == 1:
            scenario = "10% missing"
            threshold = VALIDATION_THRESHOLDS[
                model_name
            ]["10% missing"]

        else:
            scenario = "25% missing"
            threshold = VALIDATION_THRESHOLDS[
                model_name
            ]["25% missing"]

    else:

        model = v2_model
        preprocessor = v2_preprocessor
        model_name = "Missingness-Aware V2"

        if missing_count <= 7:
            scenario = "40% missing"
            threshold = VALIDATION_THRESHOLDS[
                model_name
            ]["40% missing"]

        elif missing_count <= 11:
            scenario = "60% missing"
            threshold = VALIDATION_THRESHOLDS[
                model_name
            ]["60% missing"]

        else:
            scenario = "100% missing"
            threshold = VALIDATION_THRESHOLDS[
                model_name
            ]["100% missing"]

    return {
        "model": model,
        "preprocessor": preprocessor,
        "model_name": model_name,
        "scenario": scenario,
        "threshold": threshold,
        "missing_count": missing_count,
        "missing_percentage": round(
            missing_percentage, 2
        )
    }


# --------------------------------------------------
# 9. PREDICTION ENDPOINT
# --------------------------------------------------

@app.post("/predict")
def predict(customer: Customer):

    # Step 1: Prepare input
    try:
        data = prepare_customer_data(customer)

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Input preparation failed: {str(e)}"
        )

    # Step 2: Select model
    selection = choose_model(data)

    model = selection["model"]
    preprocessor = selection["preprocessor"]

    if model is None or preprocessor is None:
        raise HTTPException(
            status_code=503,
            detail="Required ML model or preprocessor is not loaded."
        )

    # Step 3: Preprocess and predict
    try:

        processed_data = preprocessor.transform(data)

        probability = float(
            model.predict_proba(processed_data)[0][1]
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unable to process customer information.",
                "error": str(e)
            }
        )

    # Step 4: Apply validation threshold
    threshold = selection["threshold"]

    prediction = int(
        probability >= threshold
    )

    # Step 5: Return prediction
    return {
        "status": "success",
        "selected_model": selection["model_name"],
        "scenario": selection["scenario"],
        "missing_optional_fields": selection["missing_count"],
        "missing_percentage": selection["missing_percentage"],
        "prediction": prediction,
        "result": (
            "Likely to Subscribe"
            if prediction == 1
            else "Unlikely to Subscribe"
        ),
        "subscription_probability": round(
            probability, 4
        ),
        "subscription_percentage": round(
            probability * 100, 2
        ),
        "validation_threshold": threshold
    }

