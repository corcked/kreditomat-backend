from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

from app.models.personal_data import (
    Gender, MaritalStatus, Education, EmploymentType,
    IncomeSource, LivingArrangement
)


class PersonalDataBase(BaseModel):
    """Base personal data schema"""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    birth_date: date = Field(..., description="Birth date")
    gender: Gender
    marital_status: MaritalStatus
    children_count: int = Field(default=0, ge=0, le=20)
    
    # Documents
    passport_series: str = Field(..., min_length=2, max_length=2, pattern="^[A-Z]{2}$")
    passport_number: str = Field(..., min_length=7, max_length=7, pattern="^[0-9]{7}$")
    passport_issued_by: str = Field(..., min_length=1, max_length=500)
    passport_issue_date: date
    inn: str = Field(..., min_length=9, max_length=9, pattern="^[0-9]{9}$")
    
    # Contact info
    email: Optional[str] = Field(None, max_length=255)
    region: str = Field(..., min_length=1, max_length=100)
    city: str = Field(..., min_length=1, max_length=100)
    address: str = Field(..., min_length=1, max_length=500)
    
    # Employment
    education: Education
    employment_type: EmploymentType
    workplace: Optional[str] = Field(None, max_length=255)
    position: Optional[str] = Field(None, max_length=255)
    employment_duration_months: int = Field(default=0, ge=0)
    
    # Financial
    monthly_income: Decimal = Field(..., gt=0)
    income_source: IncomeSource
    additional_income: Decimal = Field(default=Decimal("0"), ge=0)
    monthly_expenses: Decimal = Field(default=Decimal("0"), ge=0)
    existing_loans_count: int = Field(default=0, ge=0)
    existing_loans_monthly_payment: Decimal = Field(default=Decimal("0"), ge=0)
    
    # Living situation
    living_arrangement: LivingArrangement
    living_address_same_as_registration: bool = Field(default=True)
    living_address: Optional[str] = Field(None, max_length=500)
    
    @field_validator('birth_date')
    def validate_age(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 18:
            raise ValueError("Must be at least 18 years old")
        if age > 100:
            raise ValueError("Invalid birth date")
        return v
    
    @field_validator('passport_series')
    def uppercase_passport_series(cls, v: str) -> str:
        return v.upper()
    
    @field_validator('email')
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and '@' not in v:
            raise ValueError("Invalid email format")
        return v


class PersonalDataCreate(PersonalDataBase):
    """Create personal data"""
    pass


class PersonalDataUpdate(BaseModel):
    """Update personal data (partial)"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    marital_status: Optional[MaritalStatus] = None
    children_count: Optional[int] = Field(None, ge=0, le=20)
    
    # Contact info
    email: Optional[str] = Field(None, max_length=255)
    region: Optional[str] = Field(None, min_length=1, max_length=100)
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    
    # Employment
    employment_type: Optional[EmploymentType] = None
    workplace: Optional[str] = Field(None, max_length=255)
    position: Optional[str] = Field(None, max_length=255)
    employment_duration_months: Optional[int] = Field(None, ge=0)
    
    # Financial
    monthly_income: Optional[Decimal] = Field(None, gt=0)
    income_source: Optional[IncomeSource] = None
    additional_income: Optional[Decimal] = Field(None, ge=0)
    monthly_expenses: Optional[Decimal] = Field(None, ge=0)
    existing_loans_count: Optional[int] = Field(None, ge=0)
    existing_loans_monthly_payment: Optional[Decimal] = Field(None, ge=0)
    
    # Living situation
    living_arrangement: Optional[LivingArrangement] = None
    living_address_same_as_registration: Optional[bool] = None
    living_address: Optional[str] = Field(None, max_length=500)


class PersonalDataResponse(PersonalDataBase):
    """Personal data response"""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PersonalDataSummary(BaseModel):
    """Summary of personal data for display"""
    full_name: str
    age: int
    gender: Gender
    marital_status: MaritalStatus
    employment_type: EmploymentType
    monthly_income: Decimal
    has_complete_data: bool
    completion_percentage: int
    missing_fields: list[str]


class DataCompletionCheck(BaseModel):
    """Check data completion status"""
    is_complete: bool
    completion_percentage: int
    required_fields: list[str]
    missing_fields: list[str]
    optional_fields: list[str]
    missing_optional: list[str]