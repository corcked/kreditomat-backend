import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        nullable=False
    )
    
    # User data
    phone_number: Mapped[str] = Column(
        String(20), 
        unique=True, 
        nullable=False,
        index=True
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
    
    # Verification status
    is_verified: Mapped[bool] = Column(
        Boolean, 
        default=False,
        nullable=False
    )
    
    # Referral system
    referral_code: Mapped[str] = Column(
        String(8), 
        unique=True,
        nullable=False,
        index=True
    )
    referred_by_id: Mapped[Optional[uuid.UUID]] = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id"),
        nullable=True
    )
    
    # Relationships
    personal_data: Mapped[Optional["PersonalData"]] = relationship(
        "PersonalData", 
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Self-referential relationship for referrals
    referred_by: Mapped[Optional["User"]] = relationship(
        "User",
        remote_side=[id],
        backref="referrals"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_users_phone_number", "phone_number"),
        Index("ix_users_referral_code", "referral_code"),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, phone={self.phone_number})>"
    
    @property
    def referral_count(self) -> int:
        """Get the number of users referred by this user"""
        return len(self.referrals) if hasattr(self, 'referrals') else 0