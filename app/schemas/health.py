# app/schemas/health.py — Pydantic schemas for health check
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class ServiceHealth(BaseModel):
    name: str
    status: str  # operational | degraded | down
    latency_ms: Optional[float] = None
    version: Optional[str] = None
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: str  # healthy | degraded | unhealthy
    timestamp: datetime
    uptime_seconds: float
    version: str = "1.0.0"
    services: List[ServiceHealth]
    database: ServiceHealth
    api_latency_ms: float
    model_uptime_pct: float
    db_load_pct: float
