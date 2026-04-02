# app/schemas/investigation.py — Pydantic schemas for investigations
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TimelineEvent(BaseModel):
    id: str
    timestamp: str
    action: str
    user: Optional[str] = None
    details: Optional[str] = None
    type: str = "action"  # action | note | verdict | system


class InvestigationCreate(BaseModel):
    alert_id: Optional[str] = None
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    severity: str = Field(default="medium", pattern="^(high|medium|low)$")


class InvestigationResponse(BaseModel):
    id: str
    case_id: str
    alert_id: Optional[str] = None
    analyst_id: Optional[str] = None
    analyst_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    verdict: Optional[str] = None
    notes: Optional[str] = None
    timeline: Optional[List[TimelineEvent]] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InvestigationListResponse(BaseModel):
    items: List[InvestigationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class VerdictSubmit(BaseModel):
    verdict: str = Field(..., description="fraud_confirmed | false_positive | inconclusive")
    notes: Optional[str] = None
