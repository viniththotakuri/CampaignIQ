
from model_loader import (
    original_model, original_preprocessor,
    v2_model, v2_preprocessor
)

print("\n========== MODEL TEST ==========")
print("Original Model type:", type(original_model))
print("Original Preprocessor type:", type(original_preprocessor))
print("Original Model classes:", original_model.classes_)

print("\nV2 Model type:", type(v2_model))
print("V2 Preprocessor type:", type(v2_preprocessor))
print("V2 Model classes:", v2_model.classes_)
print("\nAll models and preprocessors verified successfully!")