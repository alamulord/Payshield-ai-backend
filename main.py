# main.py — PayShield AI Backend Entry Point
"""
PayShield AI Backend — FastAPI Application
Real-time digital payment fraud detection platform.

Architecture: Monolithic (production-ready for microservices extraction)
Stack: FastAPI + SQLAlchemy + SQLite (swappable to PostgreSQL)
Auth: JWT with RBAC (analyst/admin roles)
Real-time: WebSocket for live alerts and transaction feed
"""
import uuid
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.security import rate_limiter
from app.db.database import init_db, close_db
from app.services.realtime_service import ws_manager

# Import routers
from app.api.v1.auth import router as auth_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.investigations import router as investigations_router
from app.api.v1.models import router as models_router
from app.api.v1.score import router as score_router
from app.api.v1.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: init DB on startup, close on shutdown"""
    print("🚀 PayShield AI Backend starting...")
    await init_db()
    print("✅ Database initialized")

    # Auto-seed if empty
    try:
        from app.db.database import async_session
        from sqlalchemy import text
        async with async_session() as db:
            result = await db.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            if count == 0:
                print("📦 Database is empty, running seeder...")
                from app.seed import seed_data
                await seed_data()
    except Exception as e:
        print(f"⚠️ Auto-seed check: {e} — Will seed on first request or run manually")

    yield

    print("🛑 PayShield AI Backend shutting down...")
    await close_db()


app = FastAPI(
    title="PayShield AI API",
    description="Real-time digital payment fraud detection platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Rate Limiting Middleware ---
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limit middleware. O(1) amortized"""
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
        )
    response = await call_next(request)
    return response


# --- Mount API Routers ---
API_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(transactions_router, prefix=API_PREFIX)
app.include_router(alerts_router, prefix=API_PREFIX)
app.include_router(analytics_router, prefix=API_PREFIX)
app.include_router(investigations_router, prefix=API_PREFIX)
app.include_router(models_router, prefix=API_PREFIX)
app.include_router(score_router, prefix=API_PREFIX)
app.include_router(health_router, prefix=API_PREFIX)


# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alerts and transaction feed.
    Clients connect and receive broadcasts for new alerts/transactions.
    O(1) per connection, O(c) per broadcast
    """
    client_id = str(uuid.uuid4())[:8]
    await ws_manager.connect(websocket, client_id)
    try:
        while True:
            # Keep connection alive, optionally handle client messages
            data = await websocket.receive_text()
            # Echo back for ping/pong
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)


# --- Root Endpoint ---
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "PayShield AI API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health/ping",
        "websocket": "ws://localhost:8000/ws",
    }


# --- Run ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
