from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.db.session import get_db
from app.core.jwt import get_current_user
from app.models.user import User
from app.models.application import Application, ApplicationStatus
from app.models.personal_data import PersonalData
from app.models.bank_offer import BankOffer
from app.schemas.application import (
    LoanCalculatorRequest, LoanCalculatorResponse,
    PDNCalculatorRequest, PDNCalculatorResponse,
    ApplicationCreate, ApplicationResponse, ApplicationListResponse,
    PreApplicationRequest, PreApplicationResponse,
    ApplicationScoreResponse, ApplicationOffersResponse, BankOfferMatch
)
from app.services.calculator import calculate_loan_details
from app.services.pdn import (
    calculate_pdn, get_pdn_risk_level, auto_correct_loan_params,
    analyze_pdn_scenario, PDNRiskLevel
)
from app.services.scoring import calculate_total_score
from app.services.referral import ReferralService
from app.services.detection import analyze_request

router = APIRouter()


@router.post("/calculator", response_model=LoanCalculatorResponse)
async def calculate_loan(
    request: LoanCalculatorRequest
) -> LoanCalculatorResponse:
    """
    Calculate loan parameters
    
    No authentication required - public endpoint
    """
    try:
        result = calculate_loan_details(
            amount=request.amount,
            annual_rate=request.annual_rate,
            months=request.months
        )
        return LoanCalculatorResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/calculator/pdn", response_model=PDNCalculatorResponse)
async def calculate_pdn_with_correction(
    request: PDNCalculatorRequest
) -> PDNCalculatorResponse:
    """
    Calculate PDN with auto-correction
    
    No authentication required - public endpoint
    """
    # Calculate original PDN
    monthly_payment = calculate_loan_details(
        request.amount, request.annual_rate, request.months
    )["monthly_payment"]
    
    original_pdn = calculate_pdn(
        monthly_payment, request.monthly_income, request.other_monthly_payments
    )
    
    # Auto-correct if needed
    corrected = auto_correct_loan_params(
        amount=request.amount,
        annual_rate=request.annual_rate,
        months=request.months,
        monthly_income=request.monthly_income,
        other_monthly_payments=request.other_monthly_payments
    )
    
    # Analyze scenario
    analysis = analyze_pdn_scenario(
        amount=request.amount,
        annual_rate=request.annual_rate,
        months=request.months,
        monthly_income=request.monthly_income,
        other_monthly_payments=request.other_monthly_payments
    )
    
    return PDNCalculatorResponse(
        original={
            "amount": request.amount,
            "months": request.months,
            "monthly_payment": monthly_payment,
            "pdn": original_pdn,
            "risk_level": get_pdn_risk_level(original_pdn).value
        },
        corrected=corrected,
        analysis=analysis
    )


@router.post("/pre-check", response_model=PreApplicationResponse)
async def pre_application_check(
    request: PreApplicationRequest,
    db: AsyncSession = Depends(get_db)
) -> PreApplicationResponse:
    """
    Check eligibility without creating application
    
    Anonymous endpoint - no authentication required
    """
    # Check if phone number is registered
    existing_user = await db.execute(
        select(User).where(User.phone_number == request.phone_number)
    )
    user = existing_user.scalars().first()
    
    # Count matching offers
    offers_query = select(func.count(BankOffer.id)).where(
        and_(
            BankOffer.is_active == True,
            BankOffer.min_amount <= request.amount,
            BankOffer.max_amount >= request.amount,
            BankOffer.min_months <= request.months,
            BankOffer.max_months >= request.months
        )
    )
    offers_count = await db.scalar(offers_query) or 0
    
    if user:
        # Registered user - can provide more accurate estimate
        return PreApplicationResponse(
            eligible=True,
            estimated_score_range="600-800",  # Based on existing user
            available_offers_count=offers_count,
            requires_registration=False,
            message="Вы можете подать заявку на займ"
        )
    else:
        # New user
        return PreApplicationResponse(
            eligible=offers_count > 0,
            estimated_score_range="500-700",  # Conservative estimate
            available_offers_count=offers_count,
            requires_registration=True,
            message="Для подачи заявки необходима регистрация"
        )


@router.post("/", response_model=ApplicationResponse)
async def create_application(
    request_data: ApplicationCreate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ApplicationResponse:
    """
    Create new loan application
    
    Requires authentication
    """
    # Check if user has personal data
    personal_data = await db.execute(
        select(PersonalData).where(PersonalData.user_id == current_user.id)
    )
    if not personal_data.scalars().first():
        raise HTTPException(
            status_code=400,
            detail="Please complete your personal information first"
        )
    
    # Check for active applications
    active_apps = await db.execute(
        select(func.count(Application.id)).where(
            and_(
                Application.user_id == current_user.id,
                Application.status.in_([
                    ApplicationStatus.PENDING,
                    ApplicationStatus.PROCESSING,
                    ApplicationStatus.APPROVED
                ])
            )
        )
    )
    if active_apps.scalar() > 0:
        raise HTTPException(
            status_code=400,
            detail="You already have an active application"
        )
    
    # Apply referral if provided
    if request_data.referral_code:
        await ReferralService.apply_referral(
            db, current_user.id, request_data.referral_code
        )
    
    # Calculate loan details
    loan_details = calculate_loan_details(
        amount=request_data.amount,
        annual_rate=Decimal("24"),  # Default rate for calculation
        months=request_data.months
    )
    
    # Calculate PDN
    pdn = calculate_pdn(
        monthly_payment=loan_details["monthly_payment"],
        monthly_income=request_data.monthly_income,
        other_monthly_payments=request_data.other_monthly_payments
    )
    pdn_risk_level = get_pdn_risk_level(pdn)
    
    # Analyze request for fraud detection
    device_analysis = await analyze_request(http_request)
    
    # Create application
    application = Application(
        user_id=current_user.id,
        amount=request_data.amount,
        months=request_data.months,
        status=ApplicationStatus.PENDING,
        pdn=pdn,
        pdn_risk_level=pdn_risk_level,
        monthly_payment=loan_details["monthly_payment"],
        total_cost=loan_details["total_cost"],
        purpose=request_data.purpose,
        device_fingerprint=device_analysis["fingerprint"],
        ip_address=device_analysis["ip"],
        user_agent=http_request.headers.get("user-agent", "")
    )
    
    db.add(application)
    await db.commit()
    await db.refresh(application)
    
    # TODO: Trigger async scoring calculation
    
    return ApplicationResponse.model_validate(application)


@router.get("/", response_model=ApplicationListResponse)
async def list_applications(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[ApplicationStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ApplicationListResponse:
    """
    List user's applications with pagination
    
    Requires authentication
    """
    # Build query
    query = select(Application).where(Application.user_id == current_user.id)
    
    if status:
        query = query.where(Application.status == status)
    
    query = query.order_by(Application.created_at.desc())
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    applications = result.scalars().all()
    
    return ApplicationListResponse(
        items=[ApplicationResponse.model_validate(app) for app in applications],
        total=total,
        page=page,
        limit=limit,
        has_next=offset + limit < total,
        has_prev=page > 1
    )


@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ApplicationResponse:
    """
    Get application details
    
    Requires authentication and ownership
    """
    application = await db.get(Application, application_id)
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ApplicationResponse.model_validate(application)


@router.get("/{application_id}/score", response_model=ApplicationScoreResponse)
async def get_application_score(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ApplicationScoreResponse:
    """
    Get detailed scoring information for application
    
    Requires authentication and ownership
    """
    # Get application
    application = await db.get(Application, application_id)
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not application.score:
        raise HTTPException(status_code=400, detail="Score not calculated yet")
    
    # Get personal data for detailed scoring
    personal_data = await db.execute(
        select(PersonalData).where(PersonalData.user_id == current_user.id)
    )
    pd = personal_data.scalars().first()
    
    if not pd:
        raise HTTPException(status_code=400, detail="Personal data not found")
    
    # Recalculate score with details
    scoring_result = calculate_total_score(
        personal_data={
            "birth_date": pd.birth_date,
            "gender": pd.gender,
            "marital_status": pd.marital_status,
            "education": pd.education,
            "employment_type": pd.employment_type,
            "employment_duration_months": pd.employment_duration_months,
            "monthly_income": pd.monthly_income,
            "income_source": pd.income_source,
            "living_arrangement": pd.living_arrangement
        },
        pdn_risk_level=application.pdn_risk_level or PDNRiskLevel.MEDIUM,
        has_referral=current_user.referred_by_id is not None
    )
    
    return ApplicationScoreResponse(
        application_id=application_id,
        credit_score=scoring_result["credit_score"],
        category=scoring_result["category"],
        approval_probability=scoring_result["approval_probability"],
        factors=scoring_result["factors"],
        recommendations=scoring_result["recommendations"],
        calculated_at=datetime.now()
    )


@router.get("/{application_id}/offers", response_model=ApplicationOffersResponse)
async def get_application_offers(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ApplicationOffersResponse:
    """
    Get matched bank offers for application
    
    Requires authentication and ownership
    """
    # Get application
    application = await db.get(Application, application_id)
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if application.status != ApplicationStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail="Application must be approved to see offers"
        )
    
    # Get matching offers
    offers_query = select(BankOffer).where(
        and_(
            BankOffer.is_active == True,
            BankOffer.min_amount <= application.amount,
            BankOffer.max_amount >= application.amount,
            BankOffer.min_months <= application.months,
            BankOffer.max_months >= application.months,
            BankOffer.min_score <= (application.score or 0)
        )
    ).order_by(BankOffer.annual_rate)
    
    result = await db.execute(offers_query)
    offers = result.scalars().all()
    
    # Calculate details for each offer
    offer_matches = []
    best_offer_id = None
    best_overpayment = None
    
    for offer in offers:
        loan_calc = calculate_loan_details(
            amount=application.amount,
            annual_rate=offer.annual_rate,
            months=application.months
        )
        
        # Calculate match score (simplified)
        match_score = 100.0
        if offer.annual_rate > 20:
            match_score -= (offer.annual_rate - 20) * 2
        if application.score and application.score < 700:
            match_score -= (700 - application.score) / 10
        
        match_score = max(0, min(100, match_score))
        
        offer_match = BankOfferMatch(
            offer_id=offer.id,
            bank_name=offer.bank_name,
            annual_rate=offer.annual_rate,
            min_amount=offer.min_amount,
            max_amount=offer.max_amount,
            min_months=offer.min_months,
            max_months=offer.max_months,
            requirements=offer.requirements,
            monthly_payment=loan_calc["monthly_payment"],
            total_cost=loan_calc["total_cost"],
            overpayment=loan_calc["overpayment"],
            match_score=match_score
        )
        
        offer_matches.append(offer_match)
        
        # Track best offer
        if best_overpayment is None or loan_calc["overpayment"] < best_overpayment:
            best_overpayment = loan_calc["overpayment"]
            best_offer_id = offer.id
    
    return ApplicationOffersResponse(
        application_id=application_id,
        offers=offer_matches,
        best_offer_id=best_offer_id,
        total_offers=len(offer_matches)
    )


@router.post("/{application_id}/cancel", response_model=ApplicationResponse)
async def cancel_application(
    application_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ApplicationResponse:
    """
    Cancel pending application
    
    Requires authentication and ownership
    """
    application = await db.get(Application, application_id)
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    if application.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if application.status not in [ApplicationStatus.PENDING, ApplicationStatus.PROCESSING]:
        raise HTTPException(
            status_code=400,
            detail="Can only cancel pending or processing applications"
        )
    
    application.status = ApplicationStatus.CANCELLED
    await db.commit()
    await db.refresh(application)
    
    return ApplicationResponse.model_validate(application)