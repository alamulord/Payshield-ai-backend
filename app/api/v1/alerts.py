# app/api/v1/alerts.py — Alert queue endpoints
"""
Alert Router: Manages fraud alert queue with filtering, status updates, and assignment.
O(log n) lookups via indexed queries
"""
import json
import math
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from app.db.database import get_db
from app.db.models import Alert
from app.core.security import get_current_user, get_optional_user
from app.schemas.alert import (
    AlertResponse, AlertListResponse, AlertStatusUpdate,
    AlertAssign, AlertStats
)
from app.services.alert_service import get_alert_stats

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def parse_triggers(triggers_str):
    """Parse triggers JSON string to list. O(1)"""
    if not triggers_str:
        return []
    try:
        return json.loads(triggers_str)
    except (json.JSONDecodeError, TypeError):
        return []


def alert_to_response(alert: Alert) -> AlertResponse:
    """Convert Alert model to response schema. O(1)"""
    return AlertResponse(
        id=alert.id,
        case_id=alert.case_id,
        transaction_id=alert.transaction_id,
        amount=alert.amount,
        merchant=alert.merchant,
        category=alert.category,
        username=alert.username,
        country=alert.country,
        country_code=alert.country_code,
        risk_score=alert.risk_score,
        triggers=parse_triggers(alert.triggers),
        status=alert.status,
        sla=alert.sla,
        sla_color=alert.sla_color or "text-green-500",
        payment_method=alert.payment_method,
        ip_address=alert.ip_address,
        device=alert.device,
        user_agent=alert.user_agent,
        verdict=alert.verdict,
        resolved_by=alert.resolved_by,
        resolved_at=alert.resolved_at,
        timestamp=alert.timestamp or alert.created_at,
        created_at=alert.created_at,
    )


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: str = Query(None),
    risk_level: str = Query(None),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    List alerts with pagination and filters.
    O(log n) with indexes
    """
    query = select(Alert)

    # Apply filters
    if status and status not in ("All Statuses", "all"):
        query = query.where(Alert.status == status)
    if risk_level and risk_level not in ("All Risk Levels", "all"):
        if risk_level == "High":
            query = query.where(Alert.risk_score >= 80)
        elif risk_level == "Medium":
            query = query.where(and_(Alert.risk_score >= 50, Alert.risk_score < 80))
        elif risk_level == "Low":
            query = query.where(Alert.risk_score < 50)
    if search:
        query = query.where(
            or_(
                Alert.case_id.ilike(f"%{search}%"),
                Alert.merchant.ilike(f"%{search}%"),
                Alert.username.ilike(f"%{search}%"),
            )
        )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Sort and paginate
    query = query.order_by(desc(Alert.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(
        items=[alert_to_response(a) for a in alerts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/stats", response_model=AlertStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get alert queue statistics. O(n)"""
    stats = await get_alert_stats(db)
    return AlertStats(**stats)


@router.get("/{alert_id}")
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    """Get single alert detail. O(log n)"""
    result = await db.execute(
        select(Alert).where(
            or_(Alert.id == alert_id, Alert.case_id == alert_id)
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert_to_response(alert)


@router.put("/{alert_id}/status")
async def update_alert_status(
    alert_id: str,
    update: AlertStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update alert status (dismiss, investigate, resolve). O(log n)"""
    result = await db.execute(
        select(Alert).where(
            or_(Alert.id == alert_id, Alert.case_id == alert_id)
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = update.status
    if update.verdict:
        alert.verdict = update.verdict
    if update.status in ("Resolved", "Dismissed"):
        alert.resolved_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(alert)
    return alert_to_response(alert)


@router.post("/{alert_id}/assign")
async def assign_alert(
    alert_id: str,
    assignment: AlertAssign,
    db: AsyncSession = Depends(get_db),
):
    """Assign an alert to an analyst. O(log n)"""
    result = await db.execute(
        select(Alert).where(
            or_(Alert.id == alert_id, Alert.case_id == alert_id)
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "In Review"
    alert.resolved_by = assignment.analyst_id

    await db.flush()
    await db.refresh(alert)
    return {"message": "Alert assigned", "alert": alert_to_response(alert)}
