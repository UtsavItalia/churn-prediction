from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PredictionResponse(BaseModel):
    customer_id: str
    churn_probability: float
    risk_segment: str
    predicted_at: datetime
    top_features: Optional[dict] = None
    shap_values: Optional[dict] = None
    model_version: str


class BulkPredictionResponse(BaseModel):
    total_processed: int
    duration_seconds: float
    risk_distribution: dict


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float


class DashboardStats(BaseModel):
    total_customers: int
    churned_customers: int
    active_customers: int
    churn_rate: float
    critical_risk_count: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    avg_churn_probability: float
