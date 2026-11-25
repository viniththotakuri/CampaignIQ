"""
Test Suite: Model Loading & Deserialization
Verifies your friend's trained XGBoost models and preprocessor pipelines
"""

from pathlib import Path
import pytest
from model_loader import (
    original_model,
    original_preprocessor,
    v2_model,
    v2_preprocessor,
    load_artifact,
    ORIGINAL_MODEL_PATH,
    V2_MODEL_PATH
)


def test_model_artifacts_exist():
    """Verifies that all 4 serialized .pkl artifacts exist on disk."""
    assert ORIGINAL_MODEL_PATH.exists(), f"Missing artifact: {ORIGINAL_MODEL_PATH}"
    assert V2_MODEL_PATH.exists(), f"Missing artifact: {V2_MODEL_PATH}"


def test_original_xgboost_loaded():
    """Verifies that the Original XGBoost model and preprocessor loaded properly."""
    assert original_model is not None
    assert original_preprocessor is not None
    assert hasattr(original_model, "classes_")
    assert list(original_model.classes_) == [0, 1]
    assert hasattr(original_model, "predict_proba")
    assert hasattr(original_preprocessor, "transform")


def test_v2_xgboost_loaded():
    """Verifies that the Missingness-Aware V2 model and preprocessor loaded properly."""
    assert v2_model is not None
    assert v2_preprocessor is not None
    assert hasattr(v2_model, "classes_")
    assert list(v2_model.classes_) == [0, 1]
    assert hasattr(v2_model, "predict_proba")
    assert hasattr(v2_preprocessor, "transform")


def test_load_artifact_file_not_found():
    """Verifies that attempting to load a non-existent artifact raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_artifact(Path("non_existent_model_artifact_path.pkl"))
