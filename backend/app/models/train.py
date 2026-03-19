import pandas as pd
import joblib
import json
import os
from datetime import datetime

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    confusion_matrix,
    average_precision_score,
)
import xgboost as xgb

# Import feature columns definition from pipeline
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.feature_engineering import FEATURE_COLUMNS, build_feature_matrix

# Config
MODEL_VERSION = "v1.0"
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "../../artifacts")
RANDOM_STATE = 42
TEST_SIZE = 0.20  # 80/20 split

# XGBoost hyperparameters — tuned for churn data
# we can tune further with GridSearch
XGB_PARAMS = {
    "n_estimators": 300,
    "max_depth": 4,  # shallow trees reduce overfitting
    "learning_rate": 0.05,  # slow learning = better generalization
    "subsample": 0.8,  # row sampling per tree
    "colsample_bytree": 0.8,  # feature sampling per tree
    "min_child_weight": 5,  # prevents learning from tiny leaf nodes
    "scale_pos_weight": 2,  # handles class imbalance (more non-churners)
    "use_label_encoder": False,
    "eval_metric": "auc",
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
}


# ── Load Data ─────────────────────────────────────────────────────────────────
def load_data():
    csv_path = os.path.join(ARTIFACTS_DIR, "feature_matrix.csv")

    if os.path.exists(csv_path):
        print("Loading feature matrix from CSV...")
        df = pd.read_csv(csv_path)
    else:
        print("CSV not found, building from DB...")
        df = build_feature_matrix()

    # Validate all feature columns exist
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")

    X = df[FEATURE_COLUMNS].copy()
    y = df["target"].copy()

    print(f"Dataset: {X.shape[0]} customers, {X.shape[1]} features")
    print(f"Churn rate: {y.mean():.1%}")

    return X, y, df


# Train
def train(X_train, y_train, X_test, y_test):
    print("\nTraining XGBoost model...")

    model = xgb.XGBClassifier(**XGB_PARAMS)

    # Fit with early stopping on test set
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        verbose=50,  # print every 50 rounds
    )

    return model


# Evaluate
def evaluate(model, X_test, y_test):
    print("\n" + "=" * 50)
    print("MODEL EVALUATION")
    print("=" * 50)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    # Core metrics
    roc_auc = roc_auc_score(y_test, y_prob)
    avg_prec = average_precision_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred)

    print(f"\nROC-AUC Score:        {roc_auc:.4f}")
    print(f"Avg Precision Score:  {avg_prec:.4f}")

    print("\nConfusion Matrix:")
    print(f"  True Negatives:  {cm[0][0]}  (active customers correctly identified)")
    print(f"  False Positives: {cm[0][1]}  (active flagged as churning — false alarms)")
    print(f"  False Negatives: {cm[1][0]}  (churners we missed — most costly)")
    print(f"  True Positives:  {cm[1][1]}  (churners correctly caught)")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Active", "Churned"]))

    # Cross-validation for robustness check
    print("Running 5-fold cross-validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    # Rebuild a fresh model for CV (same params)
    cv_model = xgb.XGBClassifier(**XGB_PARAMS)
    cv_scores = cross_val_score(
        cv_model,
        pd.concat([X_test]),  # use full data for CV
        y_test,
        cv=cv,
        scoring="roc_auc",
    )
    print(f"CV ROC-AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    return {
        "roc_auc": round(roc_auc, 4),
        "avg_precision": round(avg_prec, 4),
        "true_negatives": int(cm[0][0]),
        "false_positives": int(cm[0][1]),
        "false_negatives": int(cm[1][0]),
        "true_positives": int(cm[1][1]),
    }


# Feature Importance
def get_feature_importance(model):
    importance = model.feature_importances_
    fi_df = pd.DataFrame(
        {"feature": FEATURE_COLUMNS, "importance": importance}
    ).sort_values("importance", ascending=False)

    print("\nTop 15 Feature Importances:")
    print(fi_df.head(15).to_string(index=False))

    return fi_df


# Save Artifacts
def save_artifacts(model, fi_df, metrics, X_train):
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    # Save model
    model_path = os.path.join(ARTIFACTS_DIR, f"churn_model_{MODEL_VERSION}.pkl")
    joblib.dump(model, model_path)
    print(f"\nModel saved: {model_path}")

    # Save feature importance as JSON (API will serve this to frontend)
    fi_path = os.path.join(ARTIFACTS_DIR, "feature_importance.json")
    fi_records = fi_df.head(15).to_dict(orient="records")
    with open(fi_path, "w") as f:
        json.dump(fi_records, f, indent=2)
    print(f"Feature importance saved: {fi_path}")

    # Save model metadata
    meta = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now().isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "n_features": len(FEATURE_COLUMNS),
        "train_size": len(X_train),
        "metrics": metrics,
        "xgb_params": {
            k: v for k, v in XGB_PARAMS.items() if k not in ["use_label_encoder"]
        },
    }
    meta_path = os.path.join(ARTIFACTS_DIR, "model_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Metadata saved: {meta_path}")


# Risk Segmentation
def assign_risk_segment(probability):
    """
    Translate raw probability into business-friendly risk tier.
    Thresholds are a business decision — adjust based on capacity
    of your customer success team to act on alerts.
    """
    if probability >= 0.75:
        return "Critical"
    elif probability >= 0.50:
        return "High"
    elif probability >= 0.25:
        return "Medium"
    else:
        return "Low"


# Main
if __name__ == "__main__":
    # 1. Load
    X, y, df = load_data()

    # 2. Split — stratified to preserve churn ratio in both sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"\nTrain: {len(X_train)} | Test: {len(X_test)}")
    print(
        f"Train churn rate: {y_train.mean():.1%} | Test churn rate: {y_test.mean():.1%}"
    )

    # 3. Train
    model = train(X_train, y_train, X_test, y_test)

    # 4. Evaluate
    metrics = evaluate(model, X_test, y_test)

    # 5. Feature importance
    fi_df = get_feature_importance(model)

    # 6. Save everything
    save_artifacts(model, fi_df, metrics, X_train)

    # 7. Preview predictions on test set
    print("\n=== Sample Predictions ===")
    y_prob = model.predict_proba(X_test)[:, 1]
    sample_df = X_test.copy()
    sample_df["actual_churn"] = y_test.values
    sample_df["churn_probability"] = y_prob.round(3)
    sample_df["risk_segment"] = [assign_risk_segment(p) for p in y_prob]

    print(
        sample_df[["churn_probability", "risk_segment", "actual_churn"]]
        .head(15)
        .to_string()
    )

    print("\nRisk segment distribution:")
    print(sample_df["risk_segment"].value_counts())
