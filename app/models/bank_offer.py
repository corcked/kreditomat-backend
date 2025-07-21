import uuid
from datetime import datetime
from typing import Optional
from decimal import Decimal
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Numeric, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped

from app.db.base import Base


class BankOffer(Base):
    __tablename__ = "bank_offers"
    
    # Primary key
    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        nullable=False
    )
    
    # Bank information
    name: Mapped[str] = Column(
        String(200), 
        nullable=False
    )
    logo_url: Mapped[Optional[str]] = Column(
        String(500), 
        nullable=True
    )
    
    # Loan limits
    min_amount: Mapped[Decimal] = Column(
        Numeric(12, 2), 
        nullable=False,
        default=1
    )
    max_amount: Mapped[Decimal] = Column(
        Numeric(12, 2), 
        nullable=False,
        default=100_000_000
    )
    
    # Interest rates
    annual_rate: Mapped[Decimal] = Column(
        Numeric(5, 2),  # 0.00 to 999.99 percent
        nullable=False
    )
    daily_rate: Mapped[Decimal] = Column(
        Numeric(5, 4),  # 0.0000 to 9.9999 percent
        nullable=False
    )
    
    # Rating and reviews
    rating: Mapped[Decimal] = Column(
        Numeric(2, 1),  # 0.0 to 9.9
        nullable=False,
        default=5.0
    )
    reviews_count: Mapped[int] = Column(
        Integer, 
        nullable=False,
        default=0
    )
    
    # Status
    is_active: Mapped[bool] = Column(
        Boolean, 
        nullable=False,
        default=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime, 
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = Column(
        DateTime, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Additional fields for business logic
    min_term_months: Mapped[int] = Column(
        Integer,
        nullable=False,
        default=1
    )
    max_term_months: Mapped[int] = Column(
        Integer,
        nullable=False,
        default=36
    )
    
    # Requirements
    min_age: Mapped[int] = Column(
        Integer,
        nullable=False,
        default=18
    )
    max_age: Mapped[int] = Column(
        Integer,
        nullable=False,
        default=65
    )
    
    # Processing time in hours
    processing_time_hours: Mapped[int] = Column(
        Integer,
        nullable=False,
        default=24
    )
    
    # Table constraints
    __table_args__ = (
        CheckConstraint('min_amount > 0', name='check_positive_min_amount'),
        CheckConstraint('max_amount > min_amount', name='check_max_greater_than_min'),
        CheckConstraint('annual_rate > 0', name='check_positive_annual_rate'),
        CheckConstraint('daily_rate > 0', name='check_positive_daily_rate'),
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
        CheckConstraint('reviews_count >= 0', name='check_non_negative_reviews'),
        Index('ix_bank_offers_active_rating', 'is_active', 'rating'),
    )
    
    def __repr__(self) -> str:
        return f"<BankOffer(id={self.id}, name={self.name}, rate={self.annual_rate}%)>"
    
    @property
    def monthly_rate(self) -> Decimal:
        """Calculate monthly interest rate from annual rate"""
        return self.annual_rate / 12
    
    def is_amount_valid(self, amount: Decimal) -> bool:
        """Check if loan amount is within bank's limits"""
        return self.min_amount <= amount <= self.max_amount
    
    def is_term_valid(self, term_months: int) -> bool:
        """Check if loan term is within bank's limits"""
        return self.min_term_months <= term_months <= self.max_term_months
    
    def is_age_valid(self, age: int) -> bool:
        """Check if applicant age is within bank's requirements"""
        return self.min_age <= age <= self.max_age