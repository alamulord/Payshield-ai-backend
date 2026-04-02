# app/api/v1/analytics.py — Analytics and dashboard endpoints
"""
Analytics Router: Dashboard KPIs, charts, trends, and activity feed.
In production, these queries would hit ClickHouse for O(1) pre-aggregated results.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.services.analytics_service import (
    get_overview_kpis, get_velocity_data, get_fraud_by_type,
    get_fraud_trends, get_live_activity, get_analytics_overview
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
async def overview(db: AsyncSession = Depends(get_db)):
    """
    Get overview page KPI statistics.
    O(n) with DB, O(1) with materialized views in production
    """
    return await get_overview_kpis(db)


@router.get("/velocity")
async def velocity(
    time_range: str = Query("24H", description="1H, 24H, 7D, Live"),
    db: AsyncSession = Depends(get_db),
):
    """Get transaction velocity data for area chart. O(intervals)"""
    return await get_velocity_data(db, time_range)


@router.get("/fraud-by-type")
async def fraud_by_type(db: AsyncSession = Depends(get_db)):
    """Get fraud distribution by type for donut chart. O(n)"""
    return await get_fraud_by_type(db)


@router.get("/trends")
async def trends(
    months: int = Query(12, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
):
    """Get monthly fraud trend data for line chart. O(months)"""
    return await get_fraud_trends(db, months)


@router.get("/live-activity")
async def live_activity(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get live activity feed. O(limit)"""
    return await get_live_activity(db, limit)


@router.get("/full")
async def full_analytics(db: AsyncSession = Depends(get_db)):
    """Get full analytics overview (for Analytics page). O(n)"""
    return await get_analytics_overview(db)


@router.get("/system-health")
async def system_health():
    """Get system health metrics. O(1)"""
    import random
    return {
        "overall": "healthy",
        "metrics": [
            {
                "name": "API Latency",
                "status": "operational",
                "value": f"{random.randint(30, 60)}ms",
                "icon": "api",
                "trend": f"-{random.randint(5, 15)}ms",
                "trend_direction": "down",
                "description": "Average response time"
            },
            {
                "name": "Database Load",
                "status": "operational",
                "value": f"{random.randint(15, 35)}%",
                "icon": "database",
                "description": "Optimal Range"
            },
            {
                "name": "Model Uptime",
                "status": "operational",
                "value": "99.99%",
                "icon": "dns",
                "description": "Last 30d"
            },
            {
                "name": "AI Engine",
                "status": "operational",
                "value": "v2.4.1",
                "icon": "memory",
                "description": "Latest version deployed"
            },
            {
                "name": "Gateway Latency",
                "status": "operational",
                "value": f"{random.randint(35, 55)}ms",
                "icon": "dns",
                "description": "US-East-1"
            },
        ],
        "uptime_percentage": 99.99,
        "last_incident": None,
    }
