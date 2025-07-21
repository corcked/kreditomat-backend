from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.jwt import create_user_token
from app.core.redis import RedisService
from app.core.utils import generate_unique_referral_code, format_phone_number
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    PhoneRequest, 
    VerifyRequest, 
    AuthResponse, 
    MessageResponse,
    ErrorResponse
)
from app.services.telegram_gateway import telegram_gateway

router = APIRouter()


@router.post(
    "/request",
    response_model=MessageResponse,
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse}
    }
)
async def request_verification_code(
    request: PhoneRequest,
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    Request OTP verification code
    
    - **phone**: Phone number in international format (+998XXXXXXXXX)
    
    Returns verification code in development mode for testing
    """
    phone = format_phone_number(request.phone)
    
    try:
        # Send verification code
        result = await telegram_gateway.send_verification_code(phone)
        
        return MessageResponse(
            success=True,
            message=result["message"],
            code=result.get("code")  # Only in dev mode
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/verify",
    response_model=AuthResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse}
    }
)
async def verify_code(
    request: VerifyRequest,
    db: Session = Depends(get_db)
) -> AuthResponse:
    """
    Verify OTP code and authenticate user
    
    - **phone**: Phone number in international format
    - **code**: 6-digit verification code
    
    Returns JWT access token on success
    """
    phone = format_phone_number(request.phone)
    
    # Verify code
    if not telegram_gateway.verify_code(phone, request.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired verification code"
        )
    
    # Check if user exists
    user = db.query(User).filter(User.phone_number == phone).first()
    is_new_user = False
    
    if not user:
        # Create new user
        user = User(
            phone_number=phone,
            is_verified=True,
            referral_code=generate_unique_referral_code(db)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        is_new_user = True
    else:
        # Update verification status
        if not user.is_verified:
            user.is_verified = True
            db.commit()
    
    # Create JWT token
    token_data = create_user_token(user)
    
    return AuthResponse(
        access_token=token_data["access_token"],
        token_type=token_data["token_type"],
        user_id=str(user.id),
        expires_in=token_data["expires_in"],
        is_new_user=is_new_user
    )


@router.post(
    "/logout",
    response_model=MessageResponse
)
async def logout(
    token: str
) -> MessageResponse:
    """
    Logout user and invalidate session
    
    - **token**: JWT access token to invalidate
    """
    # Delete session from Redis
    success = RedisService.delete_session(token)
    
    if success:
        return MessageResponse(
            success=True,
            message="Logged out successfully"
        )
    else:
        return MessageResponse(
            success=False,
            message="Session not found or already expired"
        )


@router.get(
    "/check-phone",
    response_model=Dict[str, Any],
    responses={
        400: {"model": ErrorResponse}
    }
)
async def check_phone_availability(
    phone: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check if phone number can receive Telegram messages
    
    - **phone**: Phone number to check
    
    Returns availability status and whether user exists
    """
    try:
        # Format phone number
        formatted_phone = format_phone_number(phone)
        
        # Validate format
        if not formatted_phone.startswith('+998') or len(formatted_phone) != 13:
            raise ValueError("Invalid phone number format")
        
        # Check if user exists
        user_exists = db.query(User).filter(
            User.phone_number == formatted_phone
        ).first() is not None
        
        # Check Telegram availability
        availability = await telegram_gateway.check_phone_availability(formatted_phone)
        
        return {
            "phone": formatted_phone,
            "user_exists": user_exists,
            "can_receive_telegram": availability["available"],
            "has_telegram": availability["has_telegram"]
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check phone availability"
        )