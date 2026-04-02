# app/api/v1/transactions.py — Transaction endpoints
"""
Transaction Router: CRUD operations and ingestion pipeline.
POST ingestion triggers risk scoring. O(1) per ingestion.
"""
import json
import math
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from app.db.database import get_db
from app.db.models import Transaction, Alert
from app.core.security import get_current_user, get_optional_user
from app.schemas.transaction import (
    TransactionCreate, TransactionResponse,
    TransactionListResponse, TransactionFilter
)
from app.services.scoring_service import score_transaction, get_risk_explanation
from app.services.alert_service import should_generate_alert, calculate_sla, USERNAMES
from app.services.realtime_service import ws_manager
import uuid
import random

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def generate_tx_id() -> str:
    """Generate a unique transaction ID. O(1)"""
    num = random.randint(10000, 99999)
    suffix = random.choice("ABCDEFGH")
    return f"TRX-{num}-{suffix}"


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    risk_level: str = Query(None),
    search: str = Query(None),
    sort_by: str = Query("timestamp"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    """
    List transactions with pagination and filters.
    O(log n) with indexes on status/timestamp
    """
    query = select(Transaction)

    # Apply filters
    if status and status != "all":
        query = query.where(Transaction.status == status)
    if risk_level and risk_level != "all":
        query = query.where(Transaction.risk_level == risk_level)
    if search:
        query = query.where(
            or_(
                Transaction.tx_id.ilike(f"%{search}%"),
                Transaction.merchant_name.ilike(f"%{search}%"),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    if sort_order == "desc":
        query = query.order_by(desc(getattr(Transaction, sort_by, Transaction.timestamp)))
    else:
        query = query.order_by(getattr(Transaction, sort_by, Transaction.timestamp))

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    transactions = result.scalars().all()

    return TransactionListResponse(
        items=[TransactionResponse.model_validate(tx) for tx in transactions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/{tx_id}")
async def get_transaction(
    tx_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get single transaction detail with risk breakdown.
    O(log n) via indexed lookup
    """
    result = await db.execute(
        select(Transaction).where(
            or_(Transaction.id == tx_id, Transaction.tx_id == tx_id)
        )
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Parse risk factors
    risk_factors = []
    if tx.risk_factors:
        try:
            risk_factors = json.loads(tx.risk_factors)
        except json.JSONDecodeError:
            risk_factors = []

    # Get risk explanation
    explanation = get_risk_explanation(risk_factors, tx.risk_score)

    tx_data = TransactionResponse.model_validate(tx).model_dump()
    tx_data["risk_explanation"] = explanation

    # Check for related alerts
    alert_result = await db.execute(
        select(Alert).where(Alert.transaction_id == tx.id)
    )
    related_alerts = alert_result.scalars().all()
    tx_data["related_alerts"] = [
        {"id": a.id, "case_id": a.case_id, "status": a.status}
        for a in related_alerts
    ]

    return tx_data


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    tx_data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest a new transaction — triggers risk scoring pipeline.
    O(1) ingestion + O(r) rule evaluation
    """
    # Score the transaction — O(r) where r = number of rules
    risk_score, risk_level, risk_factors = score_transaction(
        amount=tx_data.amount,
        country=tx_data.country,
        merchant_category=tx_data.merchant_category or "",
        payment_method=tx_data.payment_method,
        ip_address=tx_data.ip_address or "",
        device=tx_data.device or "",
    )

    # Determine status based on risk
    if risk_level == "high":
        status_val = random.choice(["blocked", "flagged", "fraud"])
        status_color = "red"
    elif risk_level == "medium":
        status_val = random.choice(["review", "pending"])
        status_color = "yellow"
    else:
        status_val = "completed"
        status_color = "green"

    # Country name mapping
    country_names = {
        "US": "United States", "CA": "Canada", "GB": "United Kingdom",
        "FR": "France", "DE": "Germany", "CN": "China", "JP": "Japan",
        "AU": "Australia", "BR": "Brazil", "IN": "India", "NG": "Nigeria",
        "RU": "Russia", "MX": "Mexico", "KR": "South Korea",
    }

    tx = Transaction(
        tx_id=generate_tx_id(),
        amount=tx_data.amount,
        currency=tx_data.currency,
        merchant_name=tx_data.merchant_name,
        merchant_category=tx_data.merchant_category,
        payment_method=tx_data.payment_method,
        card_last4=tx_data.card_last4,
        country=tx_data.country,
        country_name=country_names.get(tx_data.country, tx_data.country),
        ip_address=tx_data.ip_address,
        device=tx_data.device,
        risk_score=risk_score,
        risk_level=risk_level,
        risk_factors=json.dumps(risk_factors),
        status=status_val,
        status_color=status_color,
        processed_at=datetime.now(timezone.utc),
    )
    db.add(tx)
    await db.flush()
    await db.refresh(tx)

    # Generate alert if high risk — O(1)
    if should_generate_alert(risk_score, risk_level):
        sla_text, sla_color, sla_delta = calculate_sla(risk_score)
        alert = Alert(
            case_id=f"CASE-{random.randint(1000, 9999)}",
            transaction_id=tx.id,
            amount=tx.amount,
            merchant=tx.merchant_name,
            category=tx.merchant_category,
            username=random.choice(USERNAMES),
            country=country_names.get(tx.country, tx.country),
            country_code=tx.country,
            risk_score=risk_score,
            triggers=json.dumps(risk_factors),
            status="New",
            sla=sla_text,
            sla_color=sla_color,
            sla_deadline=datetime.now(timezone.utc) + sla_delta,
            payment_method=f"{tx.payment_method.upper()} •••• {tx.card_last4 or '0000'}",
            ip_address=tx.ip_address,
            device=tx.device,
        )
        db.add(alert)
        await db.flush()

        # Broadcast alert via WebSocket — O(c) where c = connected clients
        await ws_manager.broadcast_alert({
            "case_id": alert.case_id,
            "amount": alert.amount,
            "merchant": alert.merchant,
            "risk_score": alert.risk_score,
            "status": alert.status,
        })

    # Broadcast transaction — O(c)
    await ws_manager.broadcast_transaction({
        "tx_id": tx.tx_id,
        "amount": tx.amount,
        "merchant": tx.merchant_name,
        "risk_score": tx.risk_score,
        "status": tx.status,
    })

    return TransactionResponse.model_validate(tx)
