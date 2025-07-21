from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any

from app.db.session import get_db
from app.models import User, BankOffer, Application, PersonalData

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "service": "kreditomat-backend"
    }


@router.get("/health/db", response_model=Dict[str, Any])
async def database_health(db: AsyncSession = Depends(get_db)):
    """Check database connectivity and table status"""
    try:
        # Check database connection
        await db.execute(text("SELECT 1"))
        
        # Count records in each table
        users_count = await db.execute(text("SELECT COUNT(*) FROM users"))
        users = users_count.scalar()
        
        bank_offers_count = await db.execute(text("SELECT COUNT(*) FROM bank_offers"))
        offers = bank_offers_count.scalar()
        
        applications_count = await db.execute(text("SELECT COUNT(*) FROM applications"))
        applications = applications_count.scalar()
        
        personal_data_count = await db.execute(text("SELECT COUNT(*) FROM personal_data"))
        personal_data = personal_data_count.scalar()
        
        # Get table list
        tables_result = await db.execute(
            text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
        )
        tables = [row[0] for row in tables_result.fetchall()]
        
        return {
            "status": "healthy",
            "database": "connected",
            "tables": {
                "count": len(tables),
                "list": tables
            },
            "records": {
                "users": users,
                "bank_offers": offers,
                "applications": applications,
                "personal_data": personal_data
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e)
        }