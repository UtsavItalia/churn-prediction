import numpy as np
import psycopg2
from datetime import datetime, timedelta
import random
import uuid
from dotenv import load_dotenv

load_dotenv()

# Reproducibility
np.random.seed(42)
random.seed(42)

# Config
N_CUSTOMERS = 5000
START_DATE = datetime(2022, 1, 1)
END_DATE = datetime(2024, 12, 31)

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "churn_db",
    "user": "postgres",
    "password": "password",
}

# Archetype Definitions
# Each archetype has weights that shape how data is generated.
# This is the business logic baked into the data.
ARCHETYPES = {
    "healthy": {
        "weight": 0.30,  # 30% of customers
        "churn_rate": 0.05,
        "usage_trend": "stable_high",
        "support_frequency": "low",
        "billing_reliability": "high",
        "avg_tenure_days": 600,
    },
    "disengaged": {
        "weight": 0.25,
        "churn_rate": 0.60,
        "usage_trend": "declining",
        "support_frequency": "low",
        "billing_reliability": "medium",
        "avg_tenure_days": 300,
    },
    "billing_stressed": {
        "weight": 0.15,
        "churn_rate": 0.55,
        "usage_trend": "unstable",
        "support_frequency": "medium",
        "billing_reliability": "low",
        "avg_tenure_days": 250,
    },
    "support_frustrated": {
        "weight": 0.20,
        "churn_rate": 0.45,
        "usage_trend": "stable_low",
        "support_frequency": "high",
        "billing_reliability": "medium",
        "avg_tenure_days": 350,
    },
    "new_uncertain": {
        "weight": 0.10,
        "churn_rate": 0.35,
        "usage_trend": "low_flat",
        "support_frequency": "medium",
        "billing_reliability": "medium",
        "avg_tenure_days": 60,
    },
}


# Helpers
def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))


def clamp(val, lo, hi):
    return max(lo, min(hi, val))


# Customer Generator
def generate_customers():
    customers = []
    archetype_labels = []

    industries = [
        "SaaS",
        "E-commerce",
        "Healthcare",
        "Finance",
        "Manufacturing",
        "Retail",
        "Education",
        "Logistics",
    ]
    company_sizes = ["SMB", "Mid-Market", "Enterprise"]
    size_weights = [0.50, 0.35, 0.15]
    contract_types = ["Monthly", "Annual", "Multi-Year"]
    plan_tiers = ["Basic", "Pro", "Enterprise"]
    acq_channels = ["Organic", "Paid", "Referral", "Partner"]

    archetype_names = list(ARCHETYPES.keys())
    archetype_weights = [ARCHETYPES[a]["weight"] for a in archetype_names]

    for _ in range(N_CUSTOMERS):
        archetype = random.choices(archetype_names, weights=archetype_weights)[0]
        config = ARCHETYPES[archetype]

        # Tenure driven by archetype
        tenure_days = max(
            30,
            int(
                np.random.normal(
                    config["avg_tenure_days"], config["avg_tenure_days"] * 0.3
                )
            ),
        )
        created_at = END_DATE - timedelta(days=tenure_days)
        created_at = max(created_at, START_DATE)

        # Churn decision
        churned = random.random() < config["churn_rate"]
        churn_date = None
        churn_reason = None

        if churned:
            # Churn happens somewhere in the last 60% of their tenure
            churn_offset = random.randint(int(tenure_days * 0.4), tenure_days)
            churn_date = created_at + timedelta(days=churn_offset)
            churn_date = min(churn_date, END_DATE)

            churn_reasons = {
                "disengaged": [
                    "Lack of engagement",
                    "Found alternative",
                    "No longer needed",
                ],
                "billing_stressed": ["Too expensive", "Budget cuts", "Payment issues"],
                "support_frustrated": [
                    "Poor support experience",
                    "Product bugs",
                    "Unmet expectations",
                ],
                "new_uncertain": [
                    "Didn't see value",
                    "Competitor offering",
                    "Too complex",
                ],
                "healthy": [
                    "Company acquisition",
                    "Budget reallocation",
                    "Team changes",
                ],
            }
            churn_reason = random.choice(churn_reasons.get(archetype, ["Unknown"]))

        # Contract type influenced by company size
        company_size = random.choices(company_sizes, weights=size_weights)[0]
        if company_size == "Enterprise":
            contract = random.choices(contract_types, weights=[0.1, 0.4, 0.5])[0]
            plan = "Enterprise"
        elif company_size == "Mid-Market":
            contract = random.choices(contract_types, weights=[0.3, 0.6, 0.1])[0]
            plan = random.choices(["Pro", "Enterprise"], weights=[0.7, 0.3])[0]
        else:
            contract = random.choices(contract_types, weights=[0.6, 0.35, 0.05])[0]
            plan = random.choices(["Basic", "Pro"], weights=[0.6, 0.4])[0]

        customers.append(
            {
                "customer_id": f"CUST-{str(uuid.uuid4())[:8].upper()}",
                "created_at": created_at,
                "country": random.choice(
                    ["US", "UK", "Canada", "Germany", "Australia", "India", "France"]
                ),
                "industry": random.choice(industries),
                "company_size": company_size,
                "contract_type": contract,
                "plan_tier": plan,
                "acquisition_channel": random.choice(acq_channels),
                "churned": churned,
                "churn_date": churn_date,
                "churn_reason": churn_reason,
            }
        )
        archetype_labels.append(archetype)

    return customers, archetype_labels


# Usage Generator
def generate_usage(customer, archetype):
    """
    Generate monthly usage rows for a customer.
    The trend shape is the key signal XGBoost will learn from.
    """
    records = []
    config = ARCHETYPES[archetype]
    trend = config["usage_trend"]

    start = customer["created_at"].replace(day=1)
    end = customer["churn_date"] if customer["churned"] else END_DATE
    end = end.replace(day=1)

    current = start
    month_n = 0  # how many months since signup

    while current <= end:
        month_n += 1

        # Base usage shaped by trend
        if trend == "stable_high":
            base_sessions = np.random.normal(80, 10)
            base_adoption = clamp(np.random.normal(0.75, 0.08), 0.5, 1.0)
        elif trend == "declining":
            # Strong decline — this is the core disengagement signal
            decay = max(0.2, 1.0 - (month_n * 0.07))
            base_sessions = np.random.normal(70 * decay, 10)
            base_adoption = clamp(np.random.normal(0.65 * decay, 0.1), 0.05, 0.9)
        elif trend == "unstable":
            # Volatile — payment stress shows in erratic usage
            base_sessions = abs(np.random.normal(50, 25))
            base_adoption = clamp(np.random.normal(0.50, 0.20), 0.1, 0.9)
        elif trend == "stable_low":
            base_sessions = np.random.normal(35, 8)
            base_adoption = clamp(np.random.normal(0.40, 0.08), 0.1, 0.7)
        else:  # low_flat (new_uncertain)
            base_sessions = np.random.normal(25, 12)
            base_adoption = clamp(np.random.normal(0.30, 0.10), 0.05, 0.6)

        records.append(
            {
                "customer_id": customer["customer_id"],
                "month_year": current.strftime("%Y-%m-%d"),
                "active_users": max(
                    1, int(np.random.normal(5 if trend == "stable_high" else 3, 1.5))
                ),
                "feature_adoption_score": round(clamp(base_adoption, 0.0, 1.0), 3),
                "sessions_count": max(0, int(base_sessions)),
                "avg_session_duration_mins": round(abs(np.random.normal(22, 8)), 1),
                "data_processed_gb": round(
                    abs(np.random.normal(15 if trend == "stable_high" else 7, 5)), 2
                ),
                "api_calls": max(
                    0,
                    int(np.random.normal(500 if trend == "stable_high" else 200, 100)),
                ),
            }
        )

        # Advance one month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return records


# Support Ticket Generator
def generate_tickets(customer, archetype):
    records = []
    config = ARCHETYPES[archetype]
    freq = config["support_frequency"]

    # Tickets per month probability
    freq_map = {"low": 0.15, "medium": 0.40, "high": 0.80}
    monthly_p = freq_map[freq]

    start = customer["created_at"]
    end = customer["churn_date"] if customer["churned"] else END_DATE

    categories = ["Bug", "Billing", "Feature Request", "Onboarding", "Performance"]
    priorities = ["Low", "Medium", "High", "Critical"]

    # Category weights by archetype
    cat_weights = {
        "healthy": [0.2, 0.1, 0.5, 0.1, 0.1],
        "disengaged": [0.2, 0.2, 0.3, 0.2, 0.1],
        "billing_stressed": [0.1, 0.7, 0.1, 0.0, 0.1],
        "support_frustrated": [0.4, 0.1, 0.2, 0.1, 0.2],
        "new_uncertain": [0.1, 0.1, 0.2, 0.5, 0.1],
    }

    tenure_days = (end - start).days
    n_months = max(1, tenure_days // 30)

    for _ in range(n_months):
        if random.random() < monthly_p:
            created_at = random_date(start, end)
            resolution_hours = (
                np.random.normal(48, 24)
                if archetype == "support_frustrated"
                else np.random.normal(18, 10)
            )
            resolved_at = created_at + timedelta(hours=max(1, resolution_hours))

            # Frustrated customers rate lower
            if archetype == "support_frustrated":
                csat = random.choices(
                    [1, 2, 3, 4, 5], weights=[0.3, 0.3, 0.2, 0.1, 0.1]
                )[0]
            elif archetype == "healthy":
                csat = random.choices(
                    [1, 2, 3, 4, 5], weights=[0.05, 0.05, 0.1, 0.3, 0.5]
                )[0]
            else:
                csat = random.choices(
                    [1, 2, 3, 4, 5], weights=[0.1, 0.2, 0.3, 0.2, 0.2]
                )[0]

            records.append(
                {
                    "customer_id": customer["customer_id"],
                    "created_at": created_at,
                    "resolved_at": resolved_at,
                    "category": random.choices(
                        categories, weights=cat_weights[archetype]
                    )[0],
                    "priority": random.choices(
                        priorities, weights=[0.4, 0.35, 0.2, 0.05]
                    )[0],
                    "satisfaction_score": csat,
                }
            )

    return records


# Billing Generator
def generate_billing(customer, archetype):
    records = []
    config = ARCHETYPES[archetype]
    reliability = config["billing_reliability"]

    # Monthly charges by plan
    plan_charges = {"Basic": 99, "Pro": 299, "Enterprise": 999}
    base_amount = plan_charges.get(customer["plan_tier"], 199)

    start = customer["created_at"]
    end = customer["churn_date"] if customer["churned"] else END_DATE

    current = start.replace(day=1)

    while current <= end:
        # Payment behavior by reliability
        if reliability == "high":
            status = random.choices(
                ["Paid", "Late", "Failed"], weights=[0.95, 0.04, 0.01]
            )[0]
        elif reliability == "medium":
            status = random.choices(
                ["Paid", "Late", "Failed"], weights=[0.80, 0.15, 0.05]
            )[0]
        else:  # low
            status = random.choices(
                ["Paid", "Late", "Failed", "Refunded"], weights=[0.50, 0.25, 0.20, 0.05]
            )[0]

        days_to_payment = 0
        amount_paid = base_amount

        if status == "Late":
            days_to_payment = random.randint(5, 30)
        elif status == "Failed":
            days_to_payment = random.randint(15, 60)
            amount_paid = 0
        elif status == "Refunded":
            amount_paid = -base_amount

        records.append(
            {
                "customer_id": customer["customer_id"],
                "billing_date": current,
                "amount_due": base_amount,
                "amount_paid": amount_paid,
                "payment_status": status,
                "days_to_payment": days_to_payment,
            }
        )

        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return records


# Database Loader
def load_to_db(customers, all_usage, all_tickets, all_billing):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("Loading customers...")
    for c in customers:
        cur.execute(
            """
            INSERT INTO customers
                (customer_id, created_at, country, industry, company_size,
                contract_type, plan_tier, acquisition_channel,
                churned, churn_date, churn_reason)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (customer_id) DO NOTHING
        """,
            (
                c["customer_id"],
                c["created_at"],
                c["country"],
                c["industry"],
                c["company_size"],
                c["contract_type"],
                c["plan_tier"],
                c["acquisition_channel"],
                c["churned"],
                c["churn_date"],
                c["churn_reason"],
            ),
        )

    print("Loading monthly usage...")
    for row in all_usage:
        cur.execute(
            """
            INSERT INTO monthly_usage
                (customer_id, month_year, active_users, feature_adoption_score,
                sessions_count, avg_session_duration_mins,
                data_processed_gb, api_calls)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (customer_id, month_year) DO NOTHING
        """,
            (
                row["customer_id"],
                row["month_year"],
                row["active_users"],
                row["feature_adoption_score"],
                row["sessions_count"],
                row["avg_session_duration_mins"],
                row["data_processed_gb"],
                row["api_calls"],
            ),
        )

    print("Loading support tickets...")
    for row in all_tickets:
        cur.execute(
            """
            INSERT INTO support_tickets
                (customer_id, created_at, resolved_at, category,
                priority, satisfaction_score)
            VALUES (%s,%s,%s,%s,%s,%s)
        """,
            (
                row["customer_id"],
                row["created_at"],
                row["resolved_at"],
                row["category"],
                row["priority"],
                row["satisfaction_score"],
            ),
        )

    print("Loading billing history...")
    for row in all_billing:
        cur.execute(
            """
            INSERT INTO billing_history
                (customer_id, billing_date, amount_due, amount_paid,
                payment_status, days_to_payment)
            VALUES (%s,%s,%s,%s,%s,%s)
        """,
            (
                row["customer_id"],
                row["billing_date"],
                row["amount_due"],
                row["amount_paid"],
                row["payment_status"],
                row["days_to_payment"],
            ),
        )

    conn.commit()
    cur.close()
    conn.close()
    print("All data loaded successfully.")


# Main
if __name__ == "__main__":
    print(f"Generating data for {N_CUSTOMERS} customers...")

    customers, archetype_labels = generate_customers()

    all_usage = []
    all_tickets = []
    all_billing = []

    for customer, archetype in zip(customers, archetype_labels):
        all_usage += generate_usage(customer, archetype)
        all_tickets += generate_tickets(customer, archetype)
        all_billing += generate_billing(customer, archetype)

    print(f"Generated {len(all_usage)} usage rows")
    print(f"Generated {len(all_tickets)} ticket rows")
    print(f"Generated {len(all_billing)} billing rows")

    load_to_db(customers, all_usage, all_tickets, all_billing)
