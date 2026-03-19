from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import json
import time

from app.core.database import get_db
from app.models.predictor import predictor
from app.schemas.prediction import PredictionResponse, BulkPredictionResponse

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/{customer_id}", response_model=PredictionResponse)
def predict_customer(customer_id: str, db: Session = Depends(get_db)):
    """
    Run churn prediction for a single customer.
    Saves result to churn_predictions table for history tracking.
    """
    try:
        result = predictor.predict_customer(customer_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Persist prediction
    db.execute(
        text(
            """
        INSERT INTO churn_predictions
            (customer_id, predicted_at, churn_probability,
            risk_segment, model_version, top_features)
        VALUES
            (:customer_id, :predicted_at, :churn_probability,
            :risk_segment, :model_version, :top_features)
    """
        ),
        {
            "customer_id": result["customer_id"],
            "predicted_at": result["predicted_at"],
            "churn_probability": result["churn_probability"],
            "risk_segment": result["risk_segment"],
            "model_version": result["model_version"],
            "top_features": json.dumps(result["top_features"]),
        },
    )
    db.commit()

    return result


@router.post("/bulk/run", response_model=BulkPredictionResponse)
def run_bulk_predictions(db: Session = Depends(get_db)):
    """
    Run predictions for all customers.
    Called on dashboard load or scheduled nightly.
    """
    from app.pipeline.feature_engineering import fetch_raw_data

    start = time.time()
    customers, usage, tickets, billing = fetch_raw_data()
    df = predictor.predict_all(customers, usage, tickets, billing)

    # Upsert all predictions
    for _, row in df.iterrows():
        db.execute(
            text(
                """
            INSERT INTO churn_predictions
                (customer_id, predicted_at, churn_probability,
                risk_segment, model_version, top_features)
            VALUES
                (:customer_id, :predicted_at, :churn_probability,
                :risk_segment, :model_version, :top_features)
        """
            ),
            {
                "customer_id": row["customer_id"],
                "predicted_at": datetime.now(),
                "churn_probability": float(row["churn_probability"]),
                "risk_segment": row["risk_segment"],
                "model_version": predictor.model_version,
                "top_features": "{}",
            },
        )

    db.commit()

    duration = round(time.time() - start, 2)
    dist = df["risk_segment"].value_counts().to_dict()

    return {
        "total_processed": len(df),
        "duration_seconds": duration,
        "risk_distribution": dist,
    }


@router.get("/{customer_id}/history")
def get_prediction_history(customer_id: str, db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            """
        SELECT predicted_at, churn_probability,
            risk_segment, model_version
        FROM churn_predictions
        WHERE customer_id = :customer_id
        ORDER BY predicted_at ASC
    """
        ),
        {"customer_id": customer_id},
    ).fetchall()

    return [r._asdict() for r in rows]
