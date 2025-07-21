#!/usr/bin/env python3
"""Initialize database with tables and initial data"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.db.session import async_session_maker, engine
from app.db.base import Base
from app.core.config import get_settings
from app.models import *  # noqa - Import all models

settings = get_settings()


async def create_tables():
    """Create all tables"""
    print("Creating database tables...")
    
    async with engine.begin() as conn:
        # Drop all tables if in dev mode (optional)
        if settings.ENVIRONMENT == "dev":
            print("Dropping existing tables (dev mode)...")
            await conn.run_sync(Base.metadata.drop_all)
        
        # Create all tables
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
    
    print("Tables created successfully!")


async def verify_tables():
    """Verify tables were created"""
    async with async_session_maker() as session:
        # Check if tables exist
        result = await session.execute(
            text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
        )
        tables = result.fetchall()
        
        print("\nCreated tables:")
        for table in tables:
            print(f"  - {table[0]}")
        
        if not tables:
            print("  No tables found!")
        
        return len(tables) > 0


async def main():
    """Main function"""
    try:
        # Create tables
        await create_tables()
        
        # Verify
        success = await verify_tables()
        
        if success:
            print("\n✅ Database initialized successfully!")
        else:
            print("\n❌ Failed to create tables!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())