"""
Trains a simple, explainable ML model on the 4 chosen features:
age, gender, bmi, blood_glucose_level -> diabetes

We use Logistic Regression

Saves:
- model/diabetes_model.pkl   (trained pipeline: scaler + logistic regression)
"""

import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

df = pd.read_csv("dataset/diabetes.csv")

print("\nDataset Information")
df.info()

print("\nSummary Statistics")
print(df.describe())

print("\nMissing Values")
print(df.isnull().sum())

print("\nDiabetes Distribution")
print(df["diabetes"].value_counts())

print("\nGender Distribution")
print(df["gender"].value_counts())

df = df[df["gender"] != "Other"]

df["gender_encoded"] = df["gender"].map({
    "Male": 1,
    "Female": 0
})

FEATURES = ["age", "gender_encoded", "bmi", "blood_glucose_level"]
X = df[FEATURES]
y = df["diabetes"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("clf", LogisticRegression(class_weight="balanced",  max_iter=1000, random_state=42)),
])

pipeline.fit(X_train, y_train)

y_pred = pipeline.predict(X_test)
y_prob = pipeline.predict_proba(X_test)[:, 1]

print("Accuracy:", accuracy_score(y_test, y_pred))
print("ROC-AUC:", roc_auc_score(y_test, y_prob))
print(classification_report(y_test, y_pred))

# Show learned coefficients (for explainability in the app)
coefs = dict(zip(FEATURES, pipeline.named_steps["clf"].coef_[0]))
print("\nFeature coefficients (higher = pushes towards High Risk):")
for f, c in coefs.items():
    print(f"  {f}: {c:.4f}")

joblib.dump(pipeline, "model/diabetes_model.pkl")
print("\nModel saved successfully!")
