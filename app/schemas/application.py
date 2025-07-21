from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

from app.models.application import ApplicationStatus
from app.services.pdn import PDNRiskLevel


class LoanCalculatorRequest(BaseModel):
    """Request for loan calculation"""
    amount: Decimal = Field(..., gt=0, description="Loan amount")
    annual_rate: Decimal = Field(..., ge=0, le=100, description="Annual interest rate")
    months: int = Field(..., gt=0, le=36, description="Loan term in months")


class LoanCalculatorResponse(BaseModel):
    """Response with loan calculation details"""
    amount: Decimal
    annual_rate: Decimal
    months: int
    monthly_payment: Decimal
    total_cost: Decimal
    overpayment: Decimal
    overpayment_percentage: Decimal
    effective_rate: Decimal
    daily_rate: Decimal


class PDNCalculatorRequest(BaseModel):
    """Request for PDN calculation"""
    amount: Decimal = Field(..., gt=0, description="Loan amount")
    annual_rate: Decimal = Field(..., ge=0, le=100, description="Annual interest rate")
    months: int = Field(..., gt=0, le=36, description="Loan term in months")
    monthly_income: Decimal = Field(..., gt=0, description="Monthly income")
    other_monthly_payments: Decimal = Field(default=Decimal("0"), ge=0, description="Other monthly payments")


class PDNCalculatorResponse(BaseModel):
    """Response with PDN calculation and auto-correction"""
    original: Dict[str, Any]
    corrected: Dict[str, Any]
    analysis: Dict[str, Any]


class ApplicationCreate(BaseModel):
    """Create new loan application"""
    amount: Decimal = Field(..., gt=0, description="Requested loan amount")
    months: int = Field(..., gt=0, le=36, description="Requested loan term")
    monthly_income: Decimal = Field(..., gt=0, description="Monthly income")
    other_monthly_payments: Decimal = Field(default=Decimal("0"), ge=0, description="Other monthly payments")
    purpose: Optional[str] = Field(None, max_length=500, description="Loan purpose")
    referral_code: Optional[str] = Field(None, min_length=6, max_length=6, description="Referral code")

    @field_validator('referral_code')
    def uppercase_referral_code(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else None


class ApplicationResponse(BaseModel):
    """Application details response"""
    id: str
    user_id: str
    amount: Decimal
    months: int
    status: ApplicationStatus
    score: Optional[int]
    pdn: Optional[Decimal]
    pdn_risk_level: Optional[PDNRiskLevel]
    monthly_payment: Optional[Decimal]
    total_cost: Optional[Decimal]
    created_at: datetime
    updated_at: datetime
    purpose: Optional[str]
    rejection_reason: Optional[str]
    
    class Config:
        from_attributes = True


class ApplicationListResponse(BaseModel):
    """List of applications"""
    items: List[ApplicationResponse]
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool


class ApplicationStatusUpdate(BaseModel):
    """Update application status (admin only)"""
    status: ApplicationStatus
    rejection_reason: Optional[str] = None


class PreApplicationRequest(BaseModel):
    """Pre-application check request"""
    amount: Decimal = Field(..., gt=0, description="Requested loan amount")
    months: int = Field(..., gt=0, le=36, description="Requested loan term")
    phone_number: str = Field(..., description="Phone number for anonymous check")


class PreApplicationResponse(BaseModel):
    """Pre-application check response"""
    eligible: bool
    estimated_score_range: str  # e.g., "600-700"
    available_offers_count: int
    requires_registration: bool
    message: str


class ApplicationScoreResponse(BaseModel):
    """Detailed scoring information"""
    application_id: str
    credit_score: int
    category: str
    approval_probability: float
    factors: List[Dict[str, Any]]
    recommendations: List[str]
    calculated_at: datetime


class BankOfferMatch(BaseModel):
    """Bank offer matched to application"""
    offer_id: str
    bank_name: str
    annual_rate: Decimal
    min_amount: Decimal
    max_amount: Decimal
    min_months: int
    max_months: int
    requirements: List[str]
    monthly_payment: Decimal
    total_cost: Decimal
    overpayment: Decimal
    match_score: float  # 0-100 how well it matches


class ApplicationOffersResponse(BaseModel):
    """Available offers for application"""
    application_id: str
    offers: List[BankOfferMatch]
    best_offer_id: Optional[str]
    total_offers: int