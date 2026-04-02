# app/api/v1/models.py — ML Model registry endpoints
"""
Model Router: Model registry, performance metrics, and training triggers.
O(n) for listing, O(1) for individual lookups
"""
import random
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import get_db
from app.db.models import ModelRegistry
from app.schemas.model import ModelResponse, ModelListResponse, ModelPerformance, TrainRequest

router = APIRouter(prefix="/models", tags=["Models"])


@router.get("", response_model=ModelListResponse)
async def list_models(db: AsyncSession = Depends(get_db)):
    """List all registered models. O(n)"""
    result = await db.execute(
        select(ModelRegistry).order_by(desc(ModelRegistry.created_at))
    )
    models = result.scalars().all()
    return ModelListResponse(
        items=[ModelResponse.model_validate(m) for m in models],
        total=len(models),
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: str, db: AsyncSession = Depends(get_db)):
    """Get model details. O(log n)"""
    result = await db.execute(
        select(ModelRegistry).where(ModelRegistry.id == model_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelResponse.model_validate(model)


@router.get("/{model_id}/performance")
async def get_model_performance(model_id: str, db: AsyncSession = Depends(get_db)):
    """Get model performance metrics with history. O(1) (simulated)"""
    result = await db.execute(
        select(ModelRegistry).where(ModelRegistry.id == model_id)
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Generate performance history
    now = datetime.now(timezone.utc)
    history = []
    for i in range(30):
        date = now - timedelta(days=29 - i)
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "accuracy": round(0.92 + random.uniform(-0.03, 0.03), 4),
            "precision": round(0.88 + random.uniform(-0.05, 0.05), 4),
            "recall": round(0.85 + random.uniform(-0.05, 0.05), 4),
            "f1_score": round(0.86 + random.uniform(-0.04, 0.04), 4),
            "false_positive_rate": round(0.02 + random.uniform(-0.01, 0.01), 4),
            "latency_ms": round(random.uniform(15, 45), 1),
        })

    return {
        "model_id": model.id,
        "model_name": model.name,
        "version": model.version,
        "metrics": {
            "accuracy": model.accuracy,
            "precision": model.precision_score,
            "recall": model.recall,
            "f1_score": model.f1_score,
            "auc_roc": model.auc_roc,
            "false_positive_rate": model.false_positive_rate,
            "latency_ms": model.latency_ms,
        },
        "performance_history": history,
        "confusion_matrix": {
            "true_positive": random.randint(800, 1200),
            "false_positive": random.randint(20, 60),
            "true_negative": random.randint(8000, 12000),
            "false_negative": random.randint(10, 30),
        },
    }


@router.post("/train-new")
async def train_new_model(
    request: TrainRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger new model training. In production: launches Celery task.
    O(1) for job creation (actual training is O(N·T·log N))
    """
    # Get latest version
    result = await db.execute(
        select(ModelRegistry)
        .where(ModelRegistry.model_type == request.model_type)
        .order_by(desc(ModelRegistry.created_at))
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if latest:
        # Parse version and increment
        parts = latest.version.replace("v", "").split(".")
        new_version = f"v{parts[0]}.{int(parts[1]) + 1}.0"
    else:
        new_version = "v1.0.0"

    new_model = ModelRegistry(
        name=f"PayShield {request.model_type.upper()} Model",
        version=new_version,
        model_type=request.model_type,
        description=request.description or f"Auto-triggered training for {request.model_type}",
        status="training",
        is_active=False,
    )
    db.add(new_model)
    await db.flush()
    await db.refresh(new_model)

    return {
        "message": "Training job initiated",
        "model_id": new_model.id,
        "version": new_version,
        "status": "training",
        "estimated_duration": "~15 minutes",
    }
