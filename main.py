# main.py — PayShield AI Backend Entry Point
"""
PayShield AI Backend — FastAPI Application
Real-time digital payment fraud detection platform.
"""
import uuid
import asyncio
import traceback
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
    
    try:
        await init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        traceback.print_exc()
    
    yield
    
    print("🛑 Shutting down...")
    try:
        await close_db()
    except Exception as e:
        print(f"⚠️ Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="PayShield AI API",
    description="Real-time digital payment fraud detection platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware - Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate Limiting Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limit middleware"""
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.check(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
        )
    response = await call_next(request)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for debugging"""
    error_msg = f"{type(exc).__name__}: {str(exc)}"
    print(f"❌ ERROR: {error_msg}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": error_msg, "type": type(exc).__name__},
    )


# Mount API Routers
API_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(transactions_router, prefix=API_PREFIX)
app.include_router(alerts_router, prefix=API_PREFIX)
app.include_router(analytics_router, prefix=API_PREFIX)
app.include_router(investigations_router, prefix=API_PREFIX)
app.include_router(models_router, prefix=API_PREFIX)
app.include_router(score_router, prefix=API_PREFIX)
app.include_router(health_router, prefix=API_PREFIX)


# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time alerts and transactions"""
    client_id = str(uuid.uuid4())[:8]
    await ws_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)


# Root Endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "PayShield AI API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health/ping",
    }


# Simple test endpoint - no database required
@app.get("/api/v1/test")
async def test_endpoint():
    """Simple test endpoint that doesn't require database"""
    return {
        "status": "ok",
        "message": "Backend is running",
        "timestamp": str(asyncio.get_event_loop().time()),
    }


# Seed endpoint - manually trigger seeding
@app.post("/api/v1/seed")
async def seed_database():
    """Manually seed the database"""
    try:
        from app.seed import seed_data
        await seed_data()
        return {"status": "success", "message": "Database seeded"}
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
