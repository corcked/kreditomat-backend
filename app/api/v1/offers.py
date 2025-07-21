from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.db.session import get_db
from app.core.jwt import get_current_user_optional
from app.models.user import User
from app.models.bank_offer import BankOffer
from app.schemas.bank_offer import (
    BankOfferResponse, BankOfferListResponse,
    BankOfferFilter, BankOfferCalculation, BankOfferComparison
)
from app.services.calculator import calculate_loan_details

router = APIRouter()


@router.get("/", response_model=BankOfferListResponse)
async def list_bank_offers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    amount: Optional[Decimal] = Query(None, gt=0, description="Filter by loan amount"),
    months: Optional[int] = Query(None, gt=0, le=120, description="Filter by loan term"),
    min_score: Optional[int] = Query(None, ge=300, le=900, description="Filter by minimum score"),
    bank_name: Optional[str] = Query(None, description="Filter by bank name"),
    max_rate: Optional[Decimal] = Query(None, gt=0, le=100, description="Maximum annual rate"),
    online_only: Optional[bool] = Query(None, description="Only online applications"),
    sort_by: str = Query("annual_rate", description="Sort field: annual_rate, bank_name, min_amount"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
) -> BankOfferListResponse:
    """
    List available bank offers with filtering
    
    Public endpoint - authentication optional
    """
    # Build query
    query = select(BankOffer).where(BankOffer.is_active == True)
    
    # Apply filters
    if amount is not None:
        query = query.where(
            and_(
                BankOffer.min_amount <= amount,
                BankOffer.max_amount >= amount
            )
        )
    
    if months is not None:
        query = query.where(
            and_(
                BankOffer.min_months <= months,
                BankOffer.max_months >= months
            )
        )
    
    if min_score is not None:
        query = query.where(BankOffer.min_score <= min_score)
    
    if bank_name:
        query = query.where(BankOffer.bank_name.ilike(f"%{bank_name}%"))
    
    if max_rate is not None:
        query = query.where(BankOffer.annual_rate <= max_rate)
    
    if online_only:
        query = query.where(BankOffer.online_application == True)
    
    # Apply sorting
    if sort_by == "bank_name":
        query = query.order_by(BankOffer.bank_name)
    elif sort_by == "min_amount":
        query = query.order_by(BankOffer.min_amount)
    else:  # Default to annual_rate
        query = query.order_by(BankOffer.annual_rate)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    offers = result.scalars().all()
    
    return BankOfferListResponse(
        items=[BankOfferResponse.model_validate(offer) for offer in offers],
        total=total,
        page=page,
        limit=limit,
        has_next=offset + limit < total,
        has_prev=page > 1
    )


@router.get("/featured", response_model=List[BankOfferResponse])
async def get_featured_offers(
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
) -> List[BankOfferResponse]:
    """
    Get featured bank offers (highest priority)
    
    Public endpoint
    """
    query = select(BankOffer).where(
        BankOffer.is_active == True
    ).order_by(
        BankOffer.priority.desc(),
        BankOffer.annual_rate
    ).limit(limit)
    
    result = await db.execute(query)
    offers = result.scalars().all()
    
    return [BankOfferResponse.model_validate(offer) for offer in offers]


@router.get("/compare", response_model=BankOfferComparison)
async def compare_offers(
    amount: Decimal = Query(..., gt=0, description="Loan amount"),
    months: int = Query(..., gt=0, le=120, description="Loan term in months"),
    score: Optional[int] = Query(None, ge=300, le=900, description="Credit score for filtering"),
    db: AsyncSession = Depends(get_db)
) -> BankOfferComparison:
    """
    Compare bank offers for specific loan parameters
    
    Public endpoint
    """
    # Get matching offers
    query = select(BankOffer).where(
        and_(
            BankOffer.is_active == True,
            BankOffer.min_amount <= amount,
            BankOffer.max_amount >= amount,
            BankOffer.min_months <= months,
            BankOffer.max_months >= months
        )
    )
    
    if score:
        query = query.where(BankOffer.min_score <= score)
    
    query = query.order_by(BankOffer.annual_rate)
    
    result = await db.execute(query)
    offers = result.scalars().all()
    
    if not offers:
        raise HTTPException(
            status_code=404,
            detail="No offers found matching your criteria"
        )
    
    # Calculate details for each offer
    calculations = []
    best_rate_id = None
    best_overpayment_id = None
    min_rate = None
    max_rate = None
    min_overpayment = None
    
    for offer in offers:
        loan_details = calculate_loan_details(amount, offer.annual_rate, months)
        
        # Calculate commission
        commission_amount = amount * offer.commission_percent / 100
        total_cost_with_commission = loan_details["total_cost"] + commission_amount
        
        calc = BankOfferCalculation(
            offer_id=offer.id,
            bank_name=offer.bank_name,
            amount=amount,
            months=months,
            annual_rate=offer.annual_rate,
            monthly_payment=loan_details["monthly_payment"],
            total_cost=total_cost_with_commission,
            overpayment=loan_details["overpayment"] + commission_amount,
            commission_amount=commission_amount,
            effective_rate=loan_details["effective_rate"]
        )
        
        calculations.append(calc)
        
        # Track best offers
        if min_rate is None or offer.annual_rate < min_rate:
            min_rate = offer.annual_rate
            best_rate_id = offer.id
        
        if max_rate is None or offer.annual_rate > max_rate:
            max_rate = offer.annual_rate
        
        total_overpayment = loan_details["overpayment"] + commission_amount
        if min_overpayment is None or total_overpayment < min_overpayment:
            min_overpayment = total_overpayment
            best_overpayment_id = offer.id
    
    # Calculate average rate
    avg_rate = sum(offer.annual_rate for offer in offers) / len(offers)
    
    return BankOfferComparison(
        amount=amount,
        months=months,
        offers=calculations,
        best_by_rate=best_rate_id,
        best_by_overpayment=best_overpayment_id,
        average_rate=avg_rate,
        rate_range=f"{min_rate}% - {max_rate}%"
    )


@router.get("/{offer_id}", response_model=BankOfferResponse)
async def get_bank_offer(
    offer_id: str,
    db: AsyncSession = Depends(get_db)
) -> BankOfferResponse:
    """
    Get bank offer details
    
    Public endpoint
    """
    offer = await db.get(BankOffer, offer_id)
    
    if not offer or not offer.is_active:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    return BankOfferResponse.model_validate(offer)


@router.post("/{offer_id}/calculate", response_model=BankOfferCalculation)
async def calculate_offer_details(
    offer_id: str,
    amount: Decimal = Query(..., gt=0, description="Loan amount"),
    months: int = Query(..., gt=0, le=120, description="Loan term"),
    db: AsyncSession = Depends(get_db)
) -> BankOfferCalculation:
    """
    Calculate loan details for specific bank offer
    
    Public endpoint
    """
    offer = await db.get(BankOffer, offer_id)
    
    if not offer or not offer.is_active:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    # Validate parameters against offer limits
    if amount < offer.min_amount or amount > offer.max_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Amount must be between {offer.min_amount} and {offer.max_amount}"
        )
    
    if months < offer.min_months or months > offer.max_months:
        raise HTTPException(
            status_code=400,
            detail=f"Term must be between {offer.min_months} and {offer.max_months} months"
        )
    
    # Calculate loan details
    loan_details = calculate_loan_details(amount, offer.annual_rate, months)
    
    # Calculate commission
    commission_amount = amount * offer.commission_percent / 100
    
    return BankOfferCalculation(
        offer_id=offer.id,
        bank_name=offer.bank_name,
        amount=amount,
        months=months,
        annual_rate=offer.annual_rate,
        monthly_payment=loan_details["monthly_payment"],
        total_cost=loan_details["total_cost"] + commission_amount,
        overpayment=loan_details["overpayment"] + commission_amount,
        commission_amount=commission_amount,
        effective_rate=loan_details["effective_rate"]
    )


@router.get("/banks/list", response_model=List[str])
async def list_banks(
    db: AsyncSession = Depends(get_db)
) -> List[str]:
    """
    Get list of all banks
    
    Public endpoint
    """
    query = select(BankOffer.bank_name).where(
        BankOffer.is_active == True
    ).distinct().order_by(BankOffer.bank_name)
    
    result = await db.execute(query)
    banks = [row[0] for row in result]
    
    return banks


@router.get("/statistics/summary")
async def get_offers_statistics(
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get bank offers statistics
    
    Public endpoint
    """
    # Count active offers
    total_offers = await db.scalar(
        select(func.count(BankOffer.id)).where(BankOffer.is_active == True)
    )
    
    # Count banks
    total_banks = await db.scalar(
        select(func.count(func.distinct(BankOffer.bank_name))).where(
            BankOffer.is_active == True
        )
    )
    
    # Get rate statistics
    rate_stats = await db.execute(
        select(
            func.min(BankOffer.annual_rate).label("min_rate"),
            func.max(BankOffer.annual_rate).label("max_rate"),
            func.avg(BankOffer.annual_rate).label("avg_rate")
        ).where(BankOffer.is_active == True)
    )
    stats = rate_stats.first()
    
    # Get amount range
    amount_stats = await db.execute(
        select(
            func.min(BankOffer.min_amount).label("min_amount"),
            func.max(BankOffer.max_amount).label("max_amount")
        ).where(BankOffer.is_active == True)
    )
    amount_range = amount_stats.first()
    
    return {
        "total_offers": total_offers or 0,
        "total_banks": total_banks or 0,
        "rate_range": {
            "min": float(stats.min_rate) if stats and stats.min_rate else 0,
            "max": float(stats.max_rate) if stats and stats.max_rate else 0,
            "average": float(stats.avg_rate) if stats and stats.avg_rate else 0
        },
        "amount_range": {
            "min": float(amount_range.min_amount) if amount_range and amount_range.min_amount else 0,
            "max": float(amount_range.max_amount) if amount_range and amount_range.max_amount else 0
        },
        "features": {
            "online_applications": await db.scalar(
                select(func.count(BankOffer.id)).where(
                    and_(
                        BankOffer.is_active == True,
                        BankOffer.online_application == True
                    )
                )
            ) or 0,
            "early_repayment": await db.scalar(
                select(func.count(BankOffer.id)).where(
                    and_(
                        BankOffer.is_active == True,
                        BankOffer.early_repayment_allowed == True
                    )
                )
            ) or 0
        }
    }