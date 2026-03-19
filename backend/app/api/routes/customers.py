from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from typing import Any
import json

from app.core.database import get_db
from app.schemas.customer import CustomerListItem, CustomerDetail

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=List[CustomerListItem])
def list_customers(
    db: Session = Depends(get_db),
    risk_segment: Optional[str] = Query(None),
    plan_tier: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    # Build filter clause for the outer query
    having_filters = ["1=1"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if plan_tier:
        having_filters.append("c.plan_tier = :plan_tier")
        params["plan_tier"] = plan_tier

    if risk_segment:
        having_filters.append("latest.risk_segment = :risk_segment")
        params["risk_segment"] = risk_segment

    where = " AND ".join(having_filters)

    rows = db.execute(
        text(
            f"""
        SELECT
            c.customer_id, c.company_size, c.contract_type,
            c.plan_tier, c.industry, c.country, c.churned,
            c.created_at,
            latest.churn_probability,
            latest.risk_segment,
            latest.predicted_at
        FROM customers c
        LEFT JOIN (
            SELECT DISTINCT ON (customer_id)
                customer_id, churn_probability,
                risk_segment, predicted_at
            FROM churn_predictions
            ORDER BY customer_id, predicted_at DESC
        ) latest ON latest.customer_id = c.customer_id
        WHERE {where}
        ORDER BY latest.churn_probability DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """
        ),
        params,
    ).fetchall()

    return [r._asdict() for r in rows]


@router.get("/{customer_id}", response_model=CustomerDetail)
def get_customer(customer_id: str, db: Session = Depends(get_db)):
    """Single customer with full detail and latest prediction."""
    row = db.execute(
        text(
            """
        SELECT
            c.*, p.churn_probability, p.risk_segment,
            p.predicted_at, p.top_features
        FROM customers c
        LEFT JOIN LATERAL (
            SELECT churn_probability, risk_segment,
                predicted_at, top_features
            FROM churn_predictions
            WHERE customer_id = c.customer_id
            ORDER BY predicted_at DESC
            LIMIT 1
        ) p ON true
        WHERE c.customer_id = :customer_id
    """
        ),
        {"customer_id": customer_id},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = row._asdict()
    if result.get("top_features") and isinstance(result["top_features"], str):
        result["top_features"] = json.loads(result["top_features"])

    return result
