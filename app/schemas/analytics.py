# app/schemas/analytics.py — Pydantic schemas for analytics/dashboard data
from pydantic import BaseModel
from typing import List, Optional


class KPIStat(BaseModel):
    title: str
    value: str
    trend: str
    trend_direction: str  # up | down
    icon: str
    progress: Optional[float] = None
    subtitle: str
    color: str = "blue"


class OverviewResponse(BaseModel):
    kpi_stats: List[KPIStat]
    total_transactions_24h: int
    total_volume_24h: float
    fraud_rate: float
    prevention_rate: float
    active_investigations: int


class VelocityDataPoint(BaseModel):
    time: str
    volume: float
    anomalies: int


class VelocityResponse(BaseModel):
    data_points: List[VelocityDataPoint]
    total_volume: int
    total_anomalies: int
    time_range: str


class FraudByType(BaseModel):
    name: str
    count: int
    percentage: float
    color: str


class FraudByTypeResponse(BaseModel):
    types: List[FraudByType]
    total: int


class TrendDataPoint(BaseModel):
    month: str
    fraud_rate: float
    prevented_losses: float
    total_volume: float


class TrendsResponse(BaseModel):
    data: List[TrendDataPoint]
    time_range: str


class FraudByMethod(BaseModel):
    name: str
    amount: float
    percentage: float


class AnalyticsOverview(BaseModel):
    total_volume: float
    fraud_rate: float
    prevented_losses: float
    top_merchants: list
    fraud_trends: List[TrendDataPoint]
    fraud_by_method: List[FraudByMethod]


class SystemHealthMetric(BaseModel):
    name: str
    status: str  # operational | degraded | down
    value: str
    icon: str
    trend: Optional[str] = None
    trend_direction: Optional[str] = None
    description: Optional[str] = None


class SystemHealthResponse(BaseModel):
    overall: str  # healthy | warning | critical
    metrics: List[SystemHealthMetric]
    uptime_percentage: float
    last_incident: Optional[str] = None


class LiveActivityItem(BaseModel):
    id: str
    type: str  # suspicious_velocity | ip_mismatch | new_device | system_resolve
    title: str
    description: str
    severity: str  # high | medium | low | info
    color: str
    timestamp: str
    tx_id: Optional[str] = None
    action_label: Optional[str] = None
    action_type: Optional[str] = None


class LiveActivityResponse(BaseModel):
    items: List[LiveActivityItem]
    total: int
