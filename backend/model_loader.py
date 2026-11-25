
from pathlib import Path
import joblib

# Project root
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "backend"

# Original XGBoost artifacts
ORIGINAL_MODEL_PATH = MODEL_DIR / "campaigniq_xgboost.pkl"
ORIGINAL_PREPROCESSOR_PATH = (
    MODEL_DIR / "campaigniq_xgboost_preprocessor.pkl"
)

# Missingness-Aware V2 artifacts
V2_MODEL_PATH = MODEL_DIR / "campaigniq_xgboost_v2.pkl"
V2_PREPROCESSOR_PATH = (
    MODEL_DIR / "campaigniq_xgboost_v2_preprocessor.pkl"
)


def load_artifact(path):
    if not path.exists():
        raise FileNotFoundError(f"Model artifact not found: {path}")

    return joblib.load(path)


# Load both models and their matching preprocessors
original_model = load_artifact(ORIGINAL_MODEL_PATH)
original_preprocessor = load_artifact(ORIGINAL_PREPROCESSOR_PATH)

v2_model = load_artifact(V2_MODEL_PATH)
v2_preprocessor = load_artifact(V2_PREPROCESSOR_PATH)

print("Original XGBoost loaded successfully!")
print("Original preprocessor loaded successfully!")
print("Missingness-Aware V2 loaded successfully!")
print("V2 preprocessor loaded successfully!")

