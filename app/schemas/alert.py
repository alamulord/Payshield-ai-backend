# app/schemas/alert.py — Pydantic schemas for alerts
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AlertResponse(BaseModel):
    id: str
    case_id: str
    transaction_id: str
    amount: float
    merchant: str
    category: Optional[str] = None
    username: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    risk_score: float
    triggers: Optional[List[str]] = None
    status: str
    sla: Optional[str] = None
    sla_color: str = "text-green-500"
    payment_method: Optional[str] = None
    ip_address: Optional[str] = None
    device: Optional[str] = None
    user_agent: Optional[str] = None
    verdict: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    timestamp: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    items: List[AlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AlertStatusUpdate(BaseModel):
    status: str = Field(..., description="New, In Review, Resolved, Dismissed")
    verdict: Optional[str] = None
    notes: Optional[str] = None


class AlertAssign(BaseModel):
    analyst_id: str


class AlertStats(BaseModel):
    total_value_at_risk: float
    open_alerts: int
    sla_breaches: int
    total_value_change: str
    open_alerts_change: str
