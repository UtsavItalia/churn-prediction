import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
import os
from sqlalchemy import create_engine

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "churn_db",
    "user": "postgres",
    "password": "password",
}


# Data Fetcher
def fetch_raw_data():
    """Pull all 4 tables from Postgres into DataFrames."""
    engine = create_engine("postgresql://postgres:password@localhost:5432/churn_db")

    customers = pd.read_sql("SELECT * FROM customers", engine)
    usage = pd.read_sql("SELECT * FROM monthly_usage", engine)
    tickets = pd.read_sql("SELECT * FROM support_tickets", engine)
    billing = pd.read_sql("SELECT * FROM billing_history", engine)

    engine.dispose()

    # Parse dates
    customers["created_at"] = pd.to_datetime(customers["created_at"])
    customers["churn_date"] = pd.to_datetime(customers["churn_date"])
    usage["month_year"] = pd.to_datetime(usage["month_year"])
    tickets["created_at"] = pd.to_datetime(tickets["created_at"])
    tickets["resolved_at"] = pd.to_datetime(tickets["resolved_at"])
    billing["billing_date"] = pd.to_datetime(billing["billing_date"])

    print(f"Fetched {len(customers)} customers")
    print(f"Fetched {len(usage)} usage rows")
    print(f"Fetched {len(tickets)} ticket rows")
    print(f"Fetched {len(billing)} billing rows")

    return customers, usage, tickets, billing


# Usage Features
def build_usage_features(usage):
    """
    For each customer, compute:
    - Recent averages (last 3 months)
    - Lifetime averages
    - Trend slope (the most important signal)
    """
    features = []

    for customer_id, grp in usage.groupby("customer_id"):
        grp = grp.sort_values("month_year")
        n = len(grp)

        # Lifetime averages
        avg_sessions_all = grp["sessions_count"].mean()
        avg_adoption_all = grp["feature_adoption_score"].mean()

        # Last 3 months (or all if fewer)
        recent = grp.tail(3)
        avg_sessions_3m = recent["sessions_count"].mean()
        avg_adoption_3m = recent["feature_adoption_score"].mean()

        # Trend: slope of sessions over time using linear regression
        # A negative slope = declining engagement = churn risk
        if n >= 3:
            x = np.arange(n)
            sessions_slope = np.polyfit(x, grp["sessions_count"], 1)[0]
            adoption_slope = np.polyfit(x, grp["feature_adoption_score"], 1)[0]
        else:
            sessions_slope = 0.0
            adoption_slope = 0.0

        # Month over month change in last 2 months
        if n >= 2:
            sessions_mom = (
                grp["sessions_count"].iloc[-1] - grp["sessions_count"].iloc[-2]
            )
        else:
            sessions_mom = 0.0

        features.append(
            {
                "customer_id": customer_id,
                "months_active": n,
                "avg_sessions_all": round(avg_sessions_all, 2),
                "avg_sessions_3m": round(avg_sessions_3m, 2),
                "avg_adoption_all": round(avg_adoption_all, 4),
                "avg_adoption_3m": round(avg_adoption_3m, 4),
                "sessions_trend": round(sessions_slope, 4),
                "adoption_trend": round(adoption_slope, 4),
                "sessions_mom_change": round(sessions_mom, 2),
                "avg_api_calls": round(grp["api_calls"].mean(), 2),
                "avg_active_users": round(grp["active_users"].mean(), 2),
            }
        )

    return pd.DataFrame(features)


# Support Features
def build_support_features(tickets):
    """
    Aggregate ticket behavior per customer.
    CSAT and resolution time are the key signals here.
    """
    features = []

    # Customers with zero tickets need a row too
    all_customers = tickets["customer_id"].unique()

    for customer_id, grp in tickets.groupby("customer_id"):
        grp = grp.sort_values("created_at")

        # Resolution time in hours
        grp["resolution_hours"] = (
            grp["resolved_at"] - grp["created_at"]
        ).dt.total_seconds() / 3600

        # Last 3 months of tickets
        cutoff = grp["created_at"].max() - pd.DateOffset(months=3)
        recent = grp[grp["created_at"] >= cutoff]

        total = len(grp)
        billing_pct = (grp["category"] == "Billing").sum() / total
        bug_pct = (grp["category"] == "Bug").sum() / total

        features.append(
            {
                "customer_id": customer_id,
                "total_tickets": total,
                "tickets_last_3m": len(recent),
                "avg_csat": grp["satisfaction_score"].mean(),
                "min_csat": grp["satisfaction_score"].min(),
                "avg_resolution_hours": grp["resolution_hours"].mean(),
                "pct_billing_tickets": round(billing_pct, 3),
                "pct_bug_tickets": round(bug_pct, 3),
                "high_priority_tickets": (
                    grp["priority"].isin(["High", "Critical"])
                ).sum(),
            }
        )

    df = pd.DataFrame(features)

    return df


# Billing Features
def build_billing_features(billing):
    """
    Payment behavior is one of the strongest churn predictors.
    Failed payments especially.
    """
    features = []

    for customer_id, grp in billing.groupby("customer_id"):
        total = len(grp)
        failed = (grp["payment_status"] == "Failed").sum()
        late = (grp["payment_status"] == "Late").sum()
        on_time = (grp["payment_status"] == "Paid").sum()

        # Revenue at risk
        total_due = grp["amount_due"].sum()
        total_paid = grp["amount_paid"].sum()
        payment_ratio = total_paid / total_due if total_due > 0 else 1.0

        # Recent billing stress (last 3 months)
        grp_sorted = grp.sort_values("billing_date")
        recent = grp_sorted.tail(3)
        recent_failed = (recent["payment_status"] == "Failed").sum()

        features.append(
            {
                "customer_id": customer_id,
                "total_payments": total,
                "failed_payment_count": int(failed),
                "late_payment_count": int(late),
                "pct_on_time": round(on_time / total, 3) if total > 0 else 1.0,
                "avg_days_late": round(grp["days_to_payment"].mean(), 2),
                "payment_ratio": round(payment_ratio, 4),
                "recent_failed_payments": int(recent_failed),
                "avg_monthly_revenue": round(grp["amount_due"].mean(), 2),
            }
        )

    return pd.DataFrame(features)


# Customer Features
def build_customer_features(customers):
    """
    Encode categorical variables and compute tenure.
    Label encoding is fine here since XGBoost handles ordinal relationships.
    """
    df = customers[
        [
            "customer_id",
            "created_at",
            "churned",
            "company_size",
            "contract_type",
            "plan_tier",
            "acquisition_channel",
            "industry",
            "country",
        ]
    ].copy()

    # Tenure in days as of end of data period
    REFERENCE_DATE = pd.Timestamp("2024-12-31")
    df["tenure_days"] = (REFERENCE_DATE - df["created_at"]).dt.days

    # Ordinal encoding for things with clear order
    size_map = {"SMB": 0, "Mid-Market": 1, "Enterprise": 2}
    contract_map = {"Monthly": 0, "Annual": 1, "Multi-Year": 2}
    plan_map = {"Basic": 0, "Pro": 1, "Enterprise": 2}

    df["company_size_enc"] = df["company_size"].map(size_map)
    df["contract_type_enc"] = df["contract_type"].map(contract_map)
    df["plan_tier_enc"] = df["plan_tier"].map(plan_map)

    # Label encode nominal categories
    for col in ["acquisition_channel", "industry", "country"]:
        le = LabelEncoder()
        df[f"{col}_enc"] = le.fit_transform(df[col].astype(str))

    return df


# Master Feature Builder
def build_feature_matrix():
    """
    Join all feature groups into a single flat table.
    This is what the model trains on.
    """
    customers, usage, tickets, billing = fetch_raw_data()

    print("\nBuilding feature groups...")
    usage_features = build_usage_features(usage)
    support_features = build_support_features(tickets)
    billing_features = build_billing_features(billing)
    customer_features = build_customer_features(customers)

    print(f"  Usage features:    {usage_features.shape}")
    print(f"  Support features:  {support_features.shape}")
    print(f"  Billing features:  {billing_features.shape}")
    print(f"  Customer features: {customer_features.shape}")

    # Left join everything onto customer_features
    # Left join so customers with no tickets still get a row (filled with 0s)
    df = customer_features.merge(usage_features, on="customer_id", how="left")
    df = df.merge(support_features, on="customer_id", how="left")
    df = df.merge(billing_features, on="customer_id", how="left")

    # Fill NaN for customers with no tickets (they're healthy — zero is correct)
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

    # Target variable
    df["target"] = df["churned"].astype(int)

    print(f"\nFinal feature matrix: {df.shape}")
    print(f"Churn rate in matrix: {df['target'].mean():.1%}")

    return df


# Feature Columns (used by model)
FEATURE_COLUMNS = [
    # Usage
    "months_active",
    "avg_sessions_all",
    "avg_sessions_3m",
    "avg_adoption_all",
    "avg_adoption_3m",
    "sessions_trend",
    "adoption_trend",
    "sessions_mom_change",
    "avg_api_calls",
    "avg_active_users",
    # Support
    "total_tickets",
    "tickets_last_3m",
    "avg_csat",
    "min_csat",
    "avg_resolution_hours",
    "pct_billing_tickets",
    "pct_bug_tickets",
    "high_priority_tickets",
    # Billing
    "failed_payment_count",
    "late_payment_count",
    "pct_on_time",
    "avg_days_late",
    "payment_ratio",
    "recent_failed_payments",
    "avg_monthly_revenue",
    # Customer
    "tenure_days",
    "company_size_enc",
    "contract_type_enc",
    "plan_tier_enc",
    "acquisition_channel_enc",
    "industry_enc",
    "country_enc",
]

if __name__ == "__main__":
    df = build_feature_matrix()

    # Quick sanity check
    print("\nSample of feature matrix:")
    print(df[FEATURE_COLUMNS + ["target"]].describe().round(3))

    # Save for model training step
    os.makedirs("artifacts", exist_ok=True)
    df.to_csv("artifacts/feature_matrix.csv", index=False)
    print("\nSaved to artifacts/feature_matrix.csv")
