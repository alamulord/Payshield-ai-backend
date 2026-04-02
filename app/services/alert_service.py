# app/services/alert_service.py — Alert generation and management
"""
Alert Service: Generates alerts from high-risk transactions, manages SLA tracking.
O(1) per alert creation, O(n) for batch operations
"""
import json
import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.db.models import Alert, Transaction


TRIGGER_MAP = {
    "Large Amount": "Large Amount",
    "Elevated Amount": "Elevated Amount",
    "High Risk Country": "High Risk Country",
    "High Risk Merchant Category": "New Merchant",
    "Velocity Spike": "Velocity Spike",
    "New Device": "New Device",
    "Unusual Time": "Unusual Time",
    "IP Mismatch": "IP Mismatch",
}

USERNAMES = [
    "john.doe", "jane.smith", "mike.johnson", "alex.m", "sarah_k",
    "david.chen", "emma.w", "ryan.garcia", "lisa.kumar", "omar.hassan",
    "priya.patel", "tom.wilson", "nina.rodriguez", "chris.lee", "maria.santos"
]


def should_generate_alert(risk_score: float, risk_level: str) -> bool:
    """Determine if a transaction should generate an alert. O(1)"""
    if risk_level == "high":
        return True
    if risk_level == "medium" and risk_score > 55:
        return random.random() > 0.3
    return False


def calculate_sla(risk_score: float) -> tuple:
    """Calculate SLA deadline based on risk score. O(1)"""
    if risk_score >= 90:
        minutes = random.randint(5, 15)
        color = "text-red-500"
    elif risk_score >= 75:
        minutes = random.randint(15, 30)
        color = "text-red-500"
    elif risk_score >= 60:
        minutes = random.randint(30, 60)
        color = "text-yellow-500"
    else:
        minutes = random.randint(60, 120)
        color = "text-green-500"

    return f"{minutes}m", color, timedelta(minutes=minutes)


async def get_alert_stats(db: AsyncSession) -> dict:
    """Get alert statistics. O(n) where n = number of alerts"""
    # Total value at risk (open alerts)
    result = await db.execute(
        select(func.sum(Alert.amount), func.count(Alert.id))
        .where(Alert.status.in_(["New", "In Review"]))
    )
    row = result.one()
    total_value = row[0] or 0
    open_count = row[1] or 0

    # SLA breaches
    now = datetime.now(timezone.utc)
    sla_result = await db.execute(
        select(func.count(Alert.id))
        .where(
            and_(
                Alert.status.in_(["New", "In Review"]),
                Alert.sla_deadline != None,
                Alert.sla_deadline < now,
            )
        )
    )
    sla_breaches = sla_result.scalar() or 0

    return {
        "total_value_at_risk": round(total_value, 2),
        "open_alerts": open_count,
        "sla_breaches": sla_breaches,
        "total_value_change": f"+{random.randint(5, 20)}%",
        "open_alerts_change": f"+{random.randint(1, 10)}%",
    }
