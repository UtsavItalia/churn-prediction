from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CustomerBase(BaseModel):
    customer_id: str
    company_size: Optional[str]
    contract_type: Optional[str]
    plan_tier: Optional[str]
    industry: Optional[str]
    country: Optional[str]
    churned: bool
    created_at: datetime


class CustomerListItem(CustomerBase):
    churn_probability: Optional[float] = None
    risk_segment: Optional[str] = None
    predicted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustomerDetail(CustomerListItem):
    acquisition_channel: Optional[str]
    churn_date: Optional[datetime]
    churn_reason: Optional[str]
    top_features: Optional[dict] = None
