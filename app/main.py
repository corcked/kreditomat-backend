from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.core.config import get_settings
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
def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }


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