# app/api/v1/investigations.py — Investigation workflow endpoints
"""
Investigation Router: Create, list, update investigations and submit verdicts.
Analyst feedback flows back for model retraining (labels.feedback topic in production).
"""
import json
import math
import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc
from app.db.database import get_db
from app.db.models import Investigation, Alert, User
from app.core.security import get_current_user, get_optional_user
from app.schemas.investigation import (
    InvestigationCreate, InvestigationResponse,
    InvestigationListResponse, VerdictSubmit, TimelineEvent
)

router = APIRouter(prefix="/investigations", tags=["Investigations"])


def parse_timeline(timeline_str):
    """Parse timeline JSON string. O(1)"""
    if not timeline_str:
        return []
    try:
        items = json.loads(timeline_str)
        return [TimelineEvent(**item) for item in items]
    except (json.JSONDecodeError, TypeError):
        return []


def investigation_to_response(inv: Investigation) -> InvestigationResponse:
    """Convert Investigation model to response. O(1)"""
    return InvestigationResponse(
        id=inv.id,
        case_id=inv.case_id,
        alert_id=inv.alert_id,
        analyst_id=inv.analyst_id,
        analyst_name=None,
        title=inv.title,
        description=inv.description,
        severity=inv.severity,
        status=inv.status,
        verdict=inv.verdict,
        notes=inv.notes,
        timeline=parse_timeline(inv.timeline),
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        closed_at=inv.closed_at,
    )


@router.get("", response_model=InvestigationListResponse)
async def list_investigations(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: str = Query(None),
    severity: str = Query(None),
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List investigations with pagination. O(log n)"""
    query = select(Investigation)

    if status and status != "all":
        query = query.where(Investigation.status == status)
    if severity and severity != "all":
        query = query.where(Investigation.severity == severity)
    if search:
        query = query.where(
            or_(
                Investigation.case_id.ilike(f"%{search}%"),
                Investigation.title.ilike(f"%{search}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(Investigation.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    investigations = result.scalars().all()

    return InvestigationListResponse(
        items=[investigation_to_response(inv) for inv in investigations],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/{inv_id}")
async def get_investigation(inv_id: str, db: AsyncSession = Depends(get_db)):
    """Get investigation detail with timeline. O(log n)"""
    result = await db.execute(
        select(Investigation).where(
            or_(Investigation.id == inv_id, Investigation.case_id == inv_id)
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return investigation_to_response(inv)


@router.post("", response_model=InvestigationResponse, status_code=201)
async def create_investigation(
    data: InvestigationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new investigation. O(1)"""
    case_id = f"INV-{random.randint(10000, 99999)}"

    initial_timeline = [
        {
            "id": f"evt-{random.randint(1000, 9999)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "Investigation created",
            "user": "System",
            "details": f"New investigation opened: {data.title}",
            "type": "system",
        }
    ]

    inv = Investigation(
        case_id=case_id,
        alert_id=data.alert_id,
        title=data.title,
        description=data.description,
        severity=data.severity,
        status="open",
        timeline=json.dumps(initial_timeline),
    )
    db.add(inv)
    await db.flush()
    await db.refresh(inv)

    # If linked to an alert, update alert status
    if data.alert_id:
        alert_result = await db.execute(
            select(Alert).where(Alert.id == data.alert_id)
        )
        alert = alert_result.scalar_one_or_none()
        if alert:
            alert.status = "In Review"

    return investigation_to_response(inv)


@router.put("/{inv_id}/verdict")
async def submit_verdict(
    inv_id: str,
    data: VerdictSubmit,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit investigation verdict. Updates alert and publishes to labels.feedback.
    O(1)
    """
    result = await db.execute(
        select(Investigation).where(
            or_(Investigation.id == inv_id, Investigation.case_id == inv_id)
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    inv.verdict = data.verdict
    inv.notes = data.notes
    inv.status = "closed"
    inv.closed_at = datetime.now(timezone.utc)

    # Add timeline event
    timeline = parse_timeline(inv.timeline)
    timeline.append(TimelineEvent(
        id=f"evt-{random.randint(1000, 9999)}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        action=f"Verdict submitted: {data.verdict}",
        user="Analyst",
        details=data.notes,
        type="verdict",
    ))
    inv.timeline = json.dumps([t.model_dump() for t in timeline])

    # Update linked alert
    if inv.alert_id:
        alert_result = await db.execute(
            select(Alert).where(Alert.id == inv.alert_id)
        )
        alert = alert_result.scalar_one_or_none()
        if alert:
            alert.status = "Resolved"
            alert.verdict = data.verdict
            alert.resolved_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(inv)
    return investigation_to_response(inv)
