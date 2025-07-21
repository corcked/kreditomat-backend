from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.jwt import get_current_user
from app.models.user import User
from app.services.referral import ReferralService
from app.schemas.referral import (
    ReferralCodeResponse, ReferralStatsResponse,
    ReferralTreeResponse, NetworkValueResponse,
    TopReferrersResponse, TopReferrer,
    ApplyReferralRequest, ApplyReferralResponse
)

router = APIRouter()


@router.get("/code", response_model=ReferralCodeResponse)
async def get_or_create_referral_code(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ReferralCodeResponse:
    """
    Get or create referral code for current user
    
    Requires authentication
    """
    # Get or create referral code
    code = await ReferralService.create_referral_code(db, current_user.id)
    link = ReferralService.generate_referral_link(code)
    
    return ReferralCodeResponse(
        referral_code=code,
        referral_link=link,
        created_at=datetime.now()
    )


@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ReferralStatsResponse:
    """
    Get referral statistics for current user
    
    Requires authentication
    """
    stats = await ReferralService.get_referral_stats(db, current_user.id)
    return ReferralStatsResponse(**stats)


@router.get("/tree", response_model=ReferralTreeResponse)
async def get_referral_tree(
    max_depth: int = Query(3, ge=1, le=5, description="Maximum tree depth"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ReferralTreeResponse:
    """
    Get referral tree for current user
    
    Requires authentication
    """
    tree = await ReferralService.get_referral_tree(db, current_user.id, max_depth)
    return ReferralTreeResponse(**tree)


@router.get("/network-value", response_model=NetworkValueResponse)
async def get_network_value(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> NetworkValueResponse:
    """
    Calculate network value for current user
    
    Requires authentication
    """
    value = await ReferralService.calculate_network_value(db, current_user.id)
    return NetworkValueResponse(**value)


@router.post("/apply", response_model=ApplyReferralResponse)
async def apply_referral_code(
    request: ApplyReferralRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> ApplyReferralResponse:
    """
    Apply referral code to current user
    
    Requires authentication
    """
    # Check if user already has a referrer
    if current_user.referred_by_id:
        return ApplyReferralResponse(
            success=False,
            message="You already have a referrer"
        )
    
    # Validate and apply referral code
    referrer = await ReferralService.validate_referral_code(db, request.referral_code)
    
    if not referrer:
        return ApplyReferralResponse(
            success=False,
            message="Invalid referral code"
        )
    
    # Cannot refer yourself
    if referrer.id == current_user.id:
        return ApplyReferralResponse(
            success=False,
            message="You cannot use your own referral code"
        )
    
    # Apply referral
    success = await ReferralService.apply_referral(
        db, current_user.id, request.referral_code
    )
    
    if success:
        return ApplyReferralResponse(
            success=True,
            message="Referral code applied successfully",
            referrer_bonus=float(ReferralService.REFERRER_REWARD),
            referred_bonus=float(ReferralService.REFERRED_BONUS)
        )
    else:
        return ApplyReferralResponse(
            success=False,
            message="Failed to apply referral code (limit reached or other error)"
        )


@router.get("/validate/{code}")
async def validate_referral_code(
    code: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Validate referral code (public endpoint)
    
    No authentication required
    """
    if len(code) != ReferralService.CODE_LENGTH:
        return {
            "valid": False,
            "message": "Invalid code format"
        }
    
    referrer = await ReferralService.validate_referral_code(db, code.upper())
    
    if referrer:
        return {
            "valid": True,
            "message": "Valid referral code",
            "referrer_id": referrer.id,
            "bonus_amount": float(ReferralService.REFERRED_BONUS)
        }
    else:
        return {
            "valid": False,
            "message": "Invalid or inactive referral code"
        }


@router.get("/top-referrers", response_model=TopReferrersResponse)
async def get_top_referrers(
    limit: int = Query(10, ge=1, le=50, description="Number of top referrers"),
    period_days: int = Query(30, ge=0, le=365, description="Period in days (0 for all time)"),
    db: AsyncSession = Depends(get_db)
) -> TopReferrersResponse:
    """
    Get top referrers leaderboard (public endpoint)
    
    No authentication required
    """
    top_list = await ReferralService.get_top_referrers(db, limit, period_days)
    
    return TopReferrersResponse(
        period_days=period_days,
        referrers=[TopReferrer(**ref) for ref in top_list]
    )


@router.get("/my-referrer")
async def get_my_referrer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get information about who referred current user
    
    Requires authentication
    """
    if not current_user.referred_by_id:
        return {
            "has_referrer": False,
            "message": "You were not referred by anyone"
        }
    
    # Get referrer info
    referrer = await db.get(User, current_user.referred_by_id)
    
    if not referrer:
        return {
            "has_referrer": False,
            "message": "Referrer not found"
        }
    
    return {
        "has_referrer": True,
        "referrer_id": referrer.id,
        "referrer_code": referrer.referral_code,
        "referred_date": current_user.created_at.isoformat()
    }


@router.get("/rewards/history")
async def get_rewards_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get referral rewards history
    
    Requires authentication
    """
    # This would typically query a separate rewards/transactions table
    # For now, return calculated data based on referrals
    stats = await ReferralService.get_referral_stats(db, current_user.id)
    
    return {
        "total_earned": stats["earned_rewards"],
        "pending": stats["pending_rewards"],
        "total_referrals": stats["total_referrals"],
        "active_referrals": stats["active_referrals"],
        "history": []  # Would be populated from rewards table
    }


@router.get("/promo-materials")
async def get_promo_materials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get promotional materials for sharing
    
    Requires authentication
    """
    # Ensure user has referral code
    code = await ReferralService.create_referral_code(db, current_user.id)
    link = ReferralService.generate_referral_link(code)
    
    return {
        "referral_code": code,
        "referral_link": link,
        "share_messages": {
            "telegram": f"🚀 Получите микрозайм за 5 минут в Kreditomat!\n\n"
                       f"Используйте мой код {code} при регистрации и получите бонус 10,000 сум\n\n"
                       f"Регистрация: {link}",
            
            "whatsapp": f"Нужны деньги срочно? Kreditomat поможет!\n"
                       f"Мой реферальный код: {code}\n"
                       f"Бонус при регистрации: 10,000 сум\n"
                       f"{link}",
            
            "sms": f"Kreditomat: быстрые займы. Код {code} = бонус 10k сум. {link}",
            
            "email_subject": "Приглашение в Kreditomat - бонус 10,000 сум",
            
            "email_body": f"Добрый день!\n\n"
                         f"Приглашаю вас воспользоваться сервисом Kreditomat для получения микрозаймов.\n\n"
                         f"При регистрации используйте мой реферальный код: {code}\n"
                         f"Вы получите бонус 10,000 сум на первый займ.\n\n"
                         f"Ссылка для регистрации: {link}\n\n"
                         f"С уважением,\n"
                         f"Ваш друг в Kreditomat"
        },
        "banners": [
            {
                "size": "1200x630",
                "url": f"https://kreditomat.uz/banners/social-share.jpg?code={code}",
                "platform": "facebook"
            },
            {
                "size": "1080x1080",
                "url": f"https://kreditomat.uz/banners/instagram-post.jpg?code={code}",
                "platform": "instagram"
            },
            {
                "size": "1200x675",
                "url": f"https://kreditomat.uz/banners/telegram-preview.jpg?code={code}",
                "platform": "telegram"
            }
        ]
    }