import uuid
import enum
from datetime import datetime
from typing import Optional
from decimal import Decimal
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped

from app.db.base import Base


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


class HousingStatus(str, enum.Enum):
    OWNED = "owned"
    RENTED = "rented"
    MORTGAGE = "mortgage"
    FAMILY = "family"


class MaritalStatus(str, enum.Enum):
    SINGLE = "single"
    MARRIED = "married"
    DIVORCED = "divorced"
    WIDOWED = "widowed"


class EducationLevel(str, enum.Enum):
    BASIC = "basic"
    SECONDARY = "secondary"
    HIGHER = "higher"


class EmploymentType(str, enum.Enum):
    EMPLOYED = "employed"
    SELF_EMPLOYED = "self_employed"
    UNEMPLOYED = "unemployed"
    RETIRED = "retired"
    STUDENT = "student"


class IncomeSource(str, enum.Enum):
    SALARY = "salary"
    BUSINESS = "business"
    PENSION = "pension"
    RENTAL = "rental"
    OTHER = "other"


class LivingArrangement(str, enum.Enum):
    ALONE = "alone"
    WITH_SPOUSE = "with_spouse"
    WITH_PARENTS = "with_parents"
    WITH_CHILDREN = "with_children"
    WITH_ROOMMATES = "with_roommates"


class PersonalData(Base):
    __tablename__ = "personal_data"
    
    # Primary key
    id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        nullable=False
    )
    
    # Foreign key to user (one-to-one)
    user_id: Mapped[uuid.UUID] = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )
    
    # Personal information
    age: Mapped[Optional[int]] = Column(Integer, nullable=True)
    gender: Mapped[Optional[Gender]] = Column(
        Enum(Gender),
        nullable=True
    )
    
    # Work and residence
    work_experience_months: Mapped[Optional[int]] = Column(
        Integer, 
        nullable=True
    )
    address_stability_years: Mapped[Optional[int]] = Column(
        Integer, 
        nullable=True
    )
    
    # Living situation
    housing_status: Mapped[Optional[HousingStatus]] = Column(
        Enum(HousingStatus),
        nullable=True
    )
    marital_status: Mapped[Optional[MaritalStatus]] = Column(
        Enum(MaritalStatus),
        nullable=True
    )
    education_level: Mapped[Optional[EducationLevel]] = Column(
        Enum(EducationLevel),
        nullable=True
    )
    
    # Credit history
    successful_loans_count: Mapped[int] = Column(
        Integer, 
        default=0,
        nullable=False
    )
    other_loans_monthly_payment: Mapped[Decimal] = Column(
        Numeric(12, 2), 
        default=0,
        nullable=False
    )
    
    # Device and location (auto-detected)
    region: Mapped[Optional[str]] = Column(
        String(100), 
        nullable=True
    )
    device_type: Mapped[Optional[str]] = Column(
        String(50), 
        nullable=True
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
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User", 
        back_populates="personal_data"
    )
    
    def __repr__(self) -> str:
        return f"<PersonalData(id={self.id}, user_id={self.user_id})>"
    
    @property
    def is_complete(self) -> bool:
        """Check if all required personal data fields are filled"""
        required_fields = [
            self.age,
            self.gender,
            self.work_experience_months,
            self.address_stability_years,
            self.housing_status,
            self.marital_status,
            self.education_level
        ]
        return all(field is not None for field in required_fields)