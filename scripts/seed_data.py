import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from decimal import Decimal
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.models import BankOffer, User
from app.db.base import Base
import uuid
import random
import string


def generate_referral_code():
    """Generate a random 8-character referral code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def seed_bank_offers(db: Session):
    """Create sample bank offers"""
    
    bank_offers_data = [
        {
            "name": "Kapitalbank",
            "logo_url": "https://example.com/logos/kapitalbank.png",
            "min_amount": Decimal("1000000"),
            "max_amount": Decimal("50000000"),
            "annual_rate": Decimal("24.0"),
            "daily_rate": Decimal("0.0657"),
            "rating": Decimal("4.5"),
            "reviews_count": 1250,
            "min_term_months": 3,
            "max_term_months": 36,
            "processing_time_hours": 24
        },
        {
            "name": "Ipoteka Bank",
            "logo_url": "https://example.com/logos/ipoteka.png",
            "min_amount": Decimal("500000"),
            "max_amount": Decimal("100000000"),
            "annual_rate": Decimal("22.0"),
            "daily_rate": Decimal("0.0603"),
            "rating": Decimal("4.7"),
            "reviews_count": 890,
            "min_term_months": 6,
            "max_term_months": 36,
            "processing_time_hours": 48
        },
        {
            "name": "Hamkorbank",
            "logo_url": "https://example.com/logos/hamkorbank.png",
            "min_amount": Decimal("1000000"),
            "max_amount": Decimal("30000000"),
            "annual_rate": Decimal("26.0"),
            "daily_rate": Decimal("0.0712"),
            "rating": Decimal("4.3"),
            "reviews_count": 654,
            "min_term_months": 3,
            "max_term_months": 24,
            "processing_time_hours": 12
        },
        {
            "name": "Qishloq Qurilish Bank",
            "logo_url": "https://example.com/logos/qqb.png",
            "min_amount": Decimal("2000000"),
            "max_amount": Decimal("40000000"),
            "annual_rate": Decimal("28.0"),
            "daily_rate": Decimal("0.0767"),
            "rating": Decimal("4.1"),
            "reviews_count": 432,
            "min_term_months": 6,
            "max_term_months": 36,
            "processing_time_hours": 72
        },
        {
            "name": "Turonbank",
            "logo_url": "https://example.com/logos/turonbank.png",
            "min_amount": Decimal("500000"),
            "max_amount": Decimal("25000000"),
            "annual_rate": Decimal("30.0"),
            "daily_rate": Decimal("0.0822"),
            "rating": Decimal("4.0"),
            "reviews_count": 567,
            "min_term_months": 1,
            "max_term_months": 18,
            "processing_time_hours": 6
        },
        {
            "name": "Agrobank",
            "logo_url": "https://example.com/logos/agrobank.png",
            "min_amount": Decimal("1500000"),
            "max_amount": Decimal("60000000"),
            "annual_rate": Decimal("21.0"),
            "daily_rate": Decimal("0.0575"),
            "rating": Decimal("4.6"),
            "reviews_count": 1123,
            "min_term_months": 12,
            "max_term_months": 36,
            "processing_time_hours": 36
        },
        {
            "name": "Orient Finans Bank",
            "logo_url": "https://example.com/logos/ofb.png",
            "min_amount": Decimal("1000000"),
            "max_amount": Decimal("20000000"),
            "annual_rate": Decimal("32.0"),
            "daily_rate": Decimal("0.0877"),
            "rating": Decimal("3.9"),
            "reviews_count": 234,
            "min_term_months": 1,
            "max_term_months": 12,
            "processing_time_hours": 4
        },
        {
            "name": "Tenge Bank",
            "logo_url": "https://example.com/logos/tenge.png",
            "min_amount": Decimal("3000000"),
            "max_amount": Decimal("80000000"),
            "annual_rate": Decimal("20.0"),
            "daily_rate": Decimal("0.0548"),
            "rating": Decimal("4.8"),
            "reviews_count": 2341,
            "min_term_months": 6,
            "max_term_months": 36,
            "processing_time_hours": 24
        },
        {
            "name": "Ziraat Bank",
            "logo_url": "https://example.com/logos/ziraat.png",
            "min_amount": Decimal("2000000"),
            "max_amount": Decimal("70000000"),
            "annual_rate": Decimal("23.0"),
            "daily_rate": Decimal("0.0630"),
            "rating": Decimal("4.4"),
            "reviews_count": 876,
            "min_term_months": 3,
            "max_term_months": 24,
            "processing_time_hours": 18
        },
        {
            "name": "Anor Bank",
            "logo_url": "https://example.com/logos/anor.png",
            "min_amount": Decimal("500000"),
            "max_amount": Decimal("35000000"),
            "annual_rate": Decimal("27.0"),
            "daily_rate": Decimal("0.0740"),
            "rating": Decimal("4.2"),
            "reviews_count": 543,
            "min_term_months": 1,
            "max_term_months": 36,
            "processing_time_hours": 8
        }
    ]
    
    for offer_data in bank_offers_data:
        offer = BankOffer(**offer_data)
        db.add(offer)
    
    db.commit()
    print(f"Created {len(bank_offers_data)} bank offers")


def seed_test_users(db: Session):
    """Create sample test users"""
    
    test_users = [
        {
            "phone_number": "+998901234567",
            "is_verified": True,
            "referral_code": generate_referral_code()
        },
        {
            "phone_number": "+998901234568",
            "is_verified": True,
            "referral_code": generate_referral_code()
        },
        {
            "phone_number": "+998901234569",
            "is_verified": False,
            "referral_code": generate_referral_code()
        }
    ]
    
    for user_data in test_users:
        user = User(**user_data)
        db.add(user)
    
    db.commit()
    print(f"Created {len(test_users)} test users")


def main():
    """Main function to seed the database"""
    print("Starting database seeding...")
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(BankOffer).count() > 0:
            print("Bank offers already exist, skipping...")
        else:
            seed_bank_offers(db)
        
        if db.query(User).count() > 0:
            print("Test users already exist, skipping...")
        else:
            seed_test_users(db)
        
        print("Database seeding completed!")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
        
    finally:
        db.close()


if __name__ == "__main__":
    main()