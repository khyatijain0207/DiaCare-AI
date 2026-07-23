import os
import joblib
import pandas as pd

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model")

_model = joblib.load(os.path.join(MODEL_DIR, "diabetes_model.pkl"))
FEATURES = [
    "age",
    "gender_encoded",
    "bmi",
    "blood_glucose_level"
]

# Reference healthy ranges used only to generate human-readable reasons
NORMAL_GLUCOSE_MAX = 140      # mg/dL (random/casual reading)
NORMAL_BMI_MAX = 24.9
HIGH_RISK_AGE = 45


def predict_diabetes(age, gender, bmi, blood_glucose_level):
    gender_encoded = 1 if gender.lower() == "male" else 0

    X = pd.DataFrame([[age, gender_encoded, bmi, blood_glucose_level]], columns=FEATURES)
    prediction = int(_model.predict(X)[0])
    confidence = float(_model.predict_proba(X)[0][prediction])

    reasons = []
    if blood_glucose_level > NORMAL_GLUCOSE_MAX:
        reasons.append(f"Blood glucose ({blood_glucose_level:.0f} mg/dL) is above the normal range (<140 mg/dL).")
    if bmi > NORMAL_BMI_MAX:
        reasons.append(f"BMI ({bmi:.1f}) is higher than the healthy range (18.5–24.9).")
    if age > HIGH_RISK_AGE:
        reasons.append(f"Age ({age:.0f}) is in a higher-risk bracket (45+).")
    if not reasons:
       reasons.append("Your age, BMI, and blood glucose level are within healthy ranges.")
    return {
        "prediction": prediction,               # 1 = High Risk, 0 = Low Risk
        "label": "High Risk" if prediction == 1 else "Low Risk",
        "confidence": round(confidence * 100, 1),
        "reasons": reasons,
    }
