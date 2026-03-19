from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from app.core.database import get_db
from app.models.predictor import predictor
from app.schemas.prediction import FeatureImportanceItem, DashboardStats

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/feature-importance", response_model=List[FeatureImportanceItem])
def get_feature_importance():
    """Top features driving churn predictions globally."""
    return predictor.feature_importance


@router.get("/dashboard-stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Aggregate stats for the dashboard header cards."""
    row = db.execute(
        text(
            """
        SELECT
            COUNT(*)                                        AS total_customers,
            SUM(CASE WHEN churned THEN 1 ELSE 0 END)       AS churned_customers,
            SUM(CASE WHEN NOT churned THEN 1 ELSE 0 END)   AS active_customers,
            ROUND(AVG(CASE WHEN churned THEN 1.0 ELSE 0.0
                      END)::numeric, 4)                    AS churn_rate
        FROM customers
    """
        )
    ).fetchone()

    risk = db.execute(
        text(
            """
        SELECT risk_segment, COUNT(*) AS cnt
        FROM (
            SELECT DISTINCT ON (customer_id)
                customer_id, risk_segment
            FROM churn_predictions
            ORDER BY customer_id, predicted_at DESC
        ) latest
        GROUP BY risk_segment
    """
        )
    ).fetchall()

    risk_dist = {r._mapping["risk_segment"]: r._mapping["cnt"] for r in risk}

    avg_prob = (
        db.execute(
            text(
                """
        SELECT AVG(churn_probability) FROM (
            SELECT DISTINCT ON (customer_id)
                customer_id, churn_probability
            FROM churn_predictions
            ORDER BY customer_id, predicted_at DESC
        ) latest
    """
            )
        ).scalar()
        or 0.0
    )

    row_dict = row._asdict() if row else {}

    return {
        "total_customers": row_dict.get("total_customers", 0),
        "churned_customers": row_dict.get("churned_customers", 0),
        "active_customers": row_dict.get("active_customers", 0),
        "churn_rate": float(row_dict.get("churn_rate") or 0),
        "critical_risk_count": risk_dist.get("Critical", 0),
        "high_risk_count": risk_dist.get("High", 0),
        "medium_risk_count": risk_dist.get("Medium", 0),
        "low_risk_count": risk_dist.get("Low", 0),
        "avg_churn_probability": round(float(avg_prob), 4),
    }


@router.get("/churn-trend")
def get_churn_trend(db: Session = Depends(get_db)):
    """Monthly churn trend for the line chart."""
    rows = db.execute(
        text(
            """
        SELECT
            TO_CHAR(DATE_TRUNC('month', churn_date), 'YYYY-MM') AS month,
            COUNT(*) AS churned_count
        FROM customers
        WHERE churned = true AND churn_date IS NOT NULL
        GROUP BY DATE_TRUNC('month', churn_date)
        ORDER BY DATE_TRUNC('month', churn_date)
    """
        )
    ).fetchall()

    return [r._asdict() for r in rows]


@router.get("/cohort-analysis")
def get_cohort_analysis(db: Session = Depends(get_db)):
    """
    Churn rate and avg churn probability broken down by:
    - Industry
    - Plan tier
    - Contract type
    - Company size
    - Acquisition channel
    All in one call to minimize round trips.
    """

    def query_cohort(dimension: str):
        rows = db.execute(
            text(
                f"""
            SELECT
                c.{dimension}                               AS segment,
                COUNT(*)                                    AS total,
                SUM(CASE WHEN c.churned THEN 1 ELSE 0 END) AS churned,
                ROUND(
                (AVG(CASE WHEN c.churned THEN 1.0 ELSE 0.0 END) * 100)::numeric
                , 1)                                        AS churn_rate_pct,
                ROUND(
                (AVG(p.churn_probability) * 100)::numeric
                , 1)                                        AS avg_risk_score
            FROM customers c
            LEFT JOIN (
                SELECT DISTINCT ON (customer_id)
                    customer_id, churn_probability
                FROM churn_predictions
                ORDER BY customer_id, predicted_at DESC
            ) p ON p.customer_id = c.customer_id
            WHERE c.{dimension} IS NOT NULL
            GROUP BY c.{dimension}
            ORDER BY churn_rate_pct DESC
        """
            )
        ).fetchall()
        return [r._asdict() for r in rows]

    return {
        "industry": query_cohort("industry"),
        "plan_tier": query_cohort("plan_tier"),
        "contract_type": query_cohort("contract_type"),
        "company_size": query_cohort("company_size"),
        "acquisition_channel": query_cohort("acquisition_channel"),
    }
