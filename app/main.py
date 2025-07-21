from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.orm import Session
import uvicorn
import redis
import time

from app.core.config import get_settings
from app.db.session import get_db
from app.core.redis import get_redis_client
from app.api.v1 import auth, applications, offers, personal_data, referrals

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up Kreditomat Backend...")
    yield
    # Shutdown
    print("Shutting down Kreditomat Backend...")


app = FastAPI(
    title="Kreditomat API",
    description="Backend API for Kreditomat - микрозайм агрегатор",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.ENVIRONMENT == "prod" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "name": "Kreditomat API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Basic health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0"
    }
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["database"] = f"unhealthy: {str(e)}"
    
    # Check Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["redis"] = f"unhealthy: {str(e)}"
    
    return health_status


@app.get("/api/v1/health")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with dependency status"""
    start_time = time.time()
    
    health = {
        "status": "healthy",
        "timestamp": start_time,
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
        "checks": {}
    }
    
    # Database check
    try:
        result = db.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar()
        health["checks"]["database"] = {
            "status": "healthy",
            "response_time": time.time() - start_time,
            "user_count": user_count
        }
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Redis check
    redis_start = time.time()
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        info = redis_client.info()
        health["checks"]["redis"] = {
            "status": "healthy",
            "response_time": time.time() - redis_start,
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory_human", "unknown")
        }
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # External services check (if needed)
    if settings.TELEGRAM_BOT_TOKEN:
        health["checks"]["telegram"] = {
            "status": "configured",
            "test_mode": settings.USE_TELEGRAM_TEST_DC
        }
    
    health["total_response_time"] = time.time() - start_time
    
    return health


# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["Applications"])
app.include_router(offers.router, prefix="/api/v1/offers", tags=["Bank Offers"])
app.include_router(personal_data.router, prefix="/api/v1/personal-data", tags=["Personal Data"])
app.include_router(referrals.router, prefix="/api/v1/referrals", tags=["Referrals"])


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )