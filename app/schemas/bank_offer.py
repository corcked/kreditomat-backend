from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


class BankOfferBase(BaseModel):
    """Base bank offer schema"""
    bank_name: str = Field(..., max_length=255)
    annual_rate: Decimal = Field(..., ge=0, le=100)
    min_amount: Decimal = Field(..., gt=0)
    max_amount: Decimal = Field(..., gt=0)
    min_months: int = Field(..., ge=1)
    max_months: int = Field(..., le=120)
    min_score: int = Field(..., ge=300, le=900)
    requirements: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    processing_time_hours: int = Field(default=24, ge=1)
    commission_percent: Decimal = Field(default=Decimal("0"), ge=0, le=10)
    early_repayment_allowed: bool = Field(default=True)
    online_application: bool = Field(default=True)
    

class BankOfferCreate(BankOfferBase):
    """Create bank offer (admin only)"""
    is_active: bool = Field(default=True)
    priority: int = Field(default=0)


class BankOfferUpdate(BaseModel):
    """Update bank offer (admin only)"""
    bank_name: Optional[str] = Field(None, max_length=255)
    annual_rate: Optional[Decimal] = Field(None, ge=0, le=100)
    min_amount: Optional[Decimal] = Field(None, gt=0)
    max_amount: Optional[Decimal] = Field(None, gt=0)
    min_months: Optional[int] = Field(None, ge=1)
    max_months: Optional[int] = Field(None, le=120)
    min_score: Optional[int] = Field(None, ge=300, le=900)
    requirements: Optional[List[str]] = None
    description: Optional[str] = None
    processing_time_hours: Optional[int] = Field(None, ge=1)
    commission_percent: Optional[Decimal] = Field(None, ge=0, le=10)
    early_repayment_allowed: Optional[bool] = None
    online_application: Optional[bool] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class BankOfferResponse(BankOfferBase):
    """Bank offer response"""
    id: str
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BankOfferListResponse(BaseModel):
    """List of bank offers"""
    items: List[BankOfferResponse]
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool


class BankOfferFilter(BaseModel):
    """Filter parameters for bank offers"""
    amount: Optional[Decimal] = Field(None, gt=0, description="Loan amount to filter by")
    months: Optional[int] = Field(None, gt=0, description="Loan term to filter by")
    min_score: Optional[int] = Field(None, ge=300, description="Minimum credit score")
    bank_name: Optional[str] = Field(None, description="Bank name filter")
    max_rate: Optional[Decimal] = Field(None, description="Maximum annual rate")
    online_only: Optional[bool] = Field(None, description="Only online applications")


class BankOfferCalculation(BaseModel):
    """Loan calculation for specific bank offer"""
    offer_id: str
    bank_name: str
    amount: Decimal
    months: int
    annual_rate: Decimal
    monthly_payment: Decimal
    total_cost: Decimal
    overpayment: Decimal
    commission_amount: Decimal
    effective_rate: Decimal


class BankOfferComparison(BaseModel):
    """Comparison of multiple bank offers"""
    amount: Decimal
    months: int
    offers: List[BankOfferCalculation]
    best_by_rate: Optional[str] = None
    best_by_overpayment: Optional[str] = None
    average_rate: Decimal
    rate_range: str  # e.g., "18.5% - 24.9%"