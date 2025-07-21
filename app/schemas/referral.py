from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ReferralCodeResponse(BaseModel):
    """Referral code response"""
    referral_code: str
    referral_link: str
    created_at: datetime


class ReferralStatsResponse(BaseModel):
    """Referral statistics response"""
    referral_code: Optional[str]
    referral_link: Optional[str]
    total_referrals: int
    active_referrals: int
    earned_rewards: float
    pending_rewards: float
    daily_limit_remaining: int
    total_limit_remaining: int
    recent_referrals: List[Dict[str, Any]]


class ReferralTreeNode(BaseModel):
    """Node in referral tree"""
    id: str
    phone: str  # Last 4 digits
    joined_at: str
    applications_count: int
    referrals: List['ReferralTreeNode'] = []


class ReferralTreeResponse(BaseModel):
    """Referral tree response"""
    id: str
    phone: str
    referral_code: Optional[str]
    referrals: List[ReferralTreeNode]


class NetworkValueResponse(BaseModel):
    """Network value metrics"""
    network_size: int
    total_loans: int
    total_loan_volume: float
    active_users_30d: int
    activity_rate: float
    estimated_lifetime_value: float


class TopReferrer(BaseModel):
    """Top referrer info"""
    user_id: str
    phone: str  # Last 4 digits
    referral_code: str
    total_referrals: int
    completed_referrals: int
    total_earnings: float


class TopReferrersResponse(BaseModel):
    """Top referrers list"""
    period_days: int
    referrers: List[TopReferrer]


class ApplyReferralRequest(BaseModel):
    """Request to apply referral code"""
    referral_code: str = Field(..., min_length=6, max_length=6)


class ApplyReferralResponse(BaseModel):
    """Response after applying referral code"""
    success: bool
    message: str
    referrer_bonus: Optional[float] = None
    referred_bonus: Optional[float] = None


# Enable forward references
ReferralTreeNode.model_rebuild()