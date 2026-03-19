import sys
import joblib
import json
import os
import pandas as pd
from datetime import datetime
import shap
import numpy as np


# Path resolution
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTIFACTS = os.path.join(BASE_DIR, "artifacts")

sys.path.insert(0, BASE_DIR)
from app.pipeline.feature_engineering import (
    FEATURE_COLUMNS,
    fetch_raw_data,
    build_usage_features,
    build_support_features,
    build_billing_features,
    build_customer_features,
)


def assign_risk_segment(probability: float) -> str:
    if probability >= 0.75:
        return "Critical"
    elif probability >= 0.50:
        return "High"
    elif probability >= 0.25:
        return "Medium"
    else:
        return "Low"


class ChurnPredictor:
    """
    Singleton-style predictor.
    Loads model once, serves predictions forever.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self, model_version: str = "v1.0"):
        if self._loaded:
            return

        model_path = os.path.join(ARTIFACTS, f"churn_model_{model_version}.pkl")
        meta_path = os.path.join(ARTIFACTS, "model_metadata.json")
        fi_path = os.path.join(ARTIFACTS, "feature_importance.json")

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")

        self.model = joblib.load(model_path)
        self.model_version = model_version

        with open(meta_path) as f:
            self.metadata = json.load(f)
        with open(fi_path) as f:
            self.feature_importance = json.load(f)

        print(f"Model loaded: {model_version}")
        self._loaded = True

    def _compute_shap_values(self, X: pd.DataFrame) -> dict:
        """
        Compute SHAP values for a single customer row.
        Returns top 5 features with their SHAP contribution scores.

        Positive SHAP = pushes toward churn
        Negative SHAP = pushes away from churn
        """
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values(X)

        # shap_values shape: (1, n_features)
        # We want the values for the single row
        values = shap_values[0]

        shap_df = pd.DataFrame(
            {
                "feature": FEATURE_COLUMNS,
                "shap_value": values,
                "abs_impact": np.abs(values),
            }
        ).sort_values("abs_impact", ascending=False)

        # Top 5 by absolute impact
        top5 = shap_df.head(5)

        return {
            row["feature"]: round(float(row["shap_value"]), 4)
            for _, row in top5.iterrows()
        }

    def _build_customer_features(self, customer_id: str) -> pd.DataFrame:
        """
        Pull raw data for a single customer and build their feature row.
        Same pipeline as training — consistency is critical.
        """
        customers, usage, tickets, billing = fetch_raw_data()

        # Filter to this customer
        cust = customers[customers["customer_id"] == customer_id]
        u = usage[usage["customer_id"] == customer_id]
        t = tickets[tickets["customer_id"] == customer_id]
        b = billing[billing["customer_id"] == customer_id]

        if cust.empty:
            raise ValueError(f"Customer not found: {customer_id}")

        # Build features using same functions as training
        cust_features = build_customer_features(cust)

        usage_features = (
            build_usage_features(u)
            if not u.empty
            else pd.DataFrame([{"customer_id": customer_id}])
        )

        support_features = (
            build_support_features(t)
            if not t.empty
            else pd.DataFrame(
                [
                    {
                        "customer_id": customer_id,
                        "total_tickets": 0,
                        "tickets_last_3m": 0,
                        "avg_csat": 0,
                        "min_csat": 0,
                        "avg_resolution_hours": 0,
                        "pct_billing_tickets": 0,
                        "pct_bug_tickets": 0,
                        "high_priority_tickets": 0,
                    }
                ]
            )
        )

        billing_features = (
            build_billing_features(b)
            if not b.empty
            else pd.DataFrame([{"customer_id": customer_id}])
        )

        # Merge
        row = cust_features.merge(usage_features, on="customer_id", how="left")
        row = row.merge(support_features, on="customer_id", how="left")
        row = row.merge(billing_features, on="customer_id", how="left")

        return row

    def predict_customer(self, customer_id: str) -> dict:
        """Run prediction for a single customer."""
        row = self._build_customer_features(customer_id)
        X = row[FEATURE_COLUMNS].fillna(0)

        prob = float(self.model.predict_proba(X)[0][1])
        segment = assign_risk_segment(prob)

        top_features = self._compute_shap_values(X)

        return {
            "customer_id": customer_id,
            "churn_probability": round(prob, 4),
            "risk_segment": segment,
            "predicted_at": datetime.now(),
            "top_features": top_features,  # now contains SHAP values
            "shap_values": top_features,  # same data, explicit field
            "model_version": self.model_version,
        }

    def predict_all(self, customers_df, usage, tickets, billing) -> pd.DataFrame:
        """
        Bulk prediction for all customers.
        Used to populate the dashboard on first load.
        """
        from app.pipeline.feature_engineering import (
            build_usage_features,
            build_support_features,
            build_billing_features,
            build_customer_features,
        )

        cust_f = build_customer_features(customers_df)
        usage_f = build_usage_features(usage)
        support_f = build_support_features(tickets)
        billing_f = build_billing_features(billing)

        df = cust_f.merge(usage_f, on="customer_id", how="left")
        df = df.merge(support_f, on="customer_id", how="left")
        df = df.merge(billing_f, on="customer_id", how="left")

        ticket_cols = [
            "total_tickets",
            "tickets_last_3m",
            "avg_csat",
            "min_csat",
            "avg_resolution_hours",
            "pct_billing_tickets",
            "pct_bug_tickets",
            "high_priority_tickets",
        ]
        df[ticket_cols] = df[ticket_cols].fillna(0)

        X = df[FEATURE_COLUMNS].fillna(0)
        probs = self.model.predict_proba(X)[:, 1]

        df["churn_probability"] = probs.round(4)
        df["risk_segment"] = [assign_risk_segment(p) for p in probs]

        return df


# Global instance — imported by routes
predictor = ChurnPredictor()
