# app/schemas/model.py — Pydantic schemas for model registry
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ModelResponse(BaseModel):
    id: str
    name: str
    version: str
    model_type: str
    description: Optional[str] = None
    accuracy: Optional[float] = None
    precision_score: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    auc_roc: Optional[float] = None
    false_positive_rate: Optional[float] = None
    latency_ms: Optional[float] = None
    status: str
    is_active: bool
    training_samples: Optional[int] = None
    feature_count: Optional[int] = None
    training_duration_sec: Optional[float] = None
    last_trained_at: Optional[datetime] = None
    drift_score: Optional[float] = None
    last_drift_check: Optional[datetime] = None
    created_at: datetime
    deployed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    items: List[ModelResponse]
    total: int


class ModelPerformance(BaseModel):
    model_id: str
    model_name: str
    version: str
    metrics: dict
    performance_history: List[dict]
    confusion_matrix: Optional[dict] = None


class TrainRequest(BaseModel):
    model_type: str = "lightgbm"
    description: Optional[str] = None
