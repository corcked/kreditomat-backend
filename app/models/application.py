import uuid
import enum
from datetime import datetime
from typing import Optional
from decimal import Decimal
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Numeric, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, validates

from app.db.base import Base


class ApplicationStatus(str, enum.Enum):
    NEW = "new"
    SENT = "sent"
    ARCHIVED = "archived"


class Application(Base):
    __tablename__ = "applications"
    
    # Primary key
    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        nullable=False
    )
    
    # Foreign key to user
    user_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id"),
        nullable=False
    )
    
    # Loan parameters
    amount: Mapped[Decimal] = Column(
        Numeric(12, 2), 
        nullable=False
    )
    term_months: Mapped[int] = Column(
        Integer, 
        nullable=False
    )
    
    # Income information
    monthly_income: Mapped[Decimal] = Column(
        Numeric(12, 2), 
        nullable=False
    )
    
    # Calculated fields
    monthly_payment: Mapped[Optional[Decimal]] = Column(
        Numeric(12, 2), 
        nullable=True
    )
    pdn_ratio: Mapped[Optional[Decimal]] = Column(
        Numeric(5, 2),  # 0.00 to 999.99 percent
        nullable=True
    )
    
    # Status
    status: Mapped[ApplicationStatus] = Column(
        Enum(ApplicationStatus),
        default=ApplicationStatus.NEW,
        nullable=False
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
    sent_at: Mapped[Optional[datetime]] = Column(
        DateTime, 
        nullable=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User", 
        back_populates="applications"
    )
    
    # Table constraints
    __table_args__ = (
        CheckConstraint('amount >= 1 AND amount <= 100000000', name='check_amount_range'),
        CheckConstraint('term_months >= 1 AND term_months <= 36', name='check_term_range'),
        CheckConstraint('monthly_income > 0', name='check_positive_income'),
        CheckConstraint('monthly_payment > 0 OR monthly_payment IS NULL', name='check_positive_payment'),
    )
    
    def __repr__(self) -> str:
        return f"<Application(id={self.id}, amount={self.amount}, status={self.status})>"
    
    @validates('amount')
    def validate_amount(self, key, value):
        """Validate loan amount is within allowed range"""
        if value < 1 or value > 100_000_000:
            raise ValueError(f"Loan amount must be between 1 and 100,000,000")
        return value
    
    @validates('term_months')
    def validate_term(self, key, value):
        """Validate loan term is within allowed range"""
        if value < 1 or value > 36:
            raise ValueError(f"Loan term must be between 1 and 36 months")
        return value
    
    @property
    def is_pdn_acceptable(self) -> bool:
        """Check if PDN ratio is within acceptable range"""
        return self.pdn_ratio is not None and self.pdn_ratio <= 50.0
    
    @property
    def total_cost(self) -> Optional[Decimal]:
        """Calculate total cost of the loan"""
        if self.monthly_payment and self.term_months:
            return self.monthly_payment * self.term_months
        return None