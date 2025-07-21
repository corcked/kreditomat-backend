import random
import string
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.application import Application, ApplicationStatus
from app.core.config import get_settings

settings = get_settings()


class ReferralService:
    """Service for managing referral system"""
    
    # Referral code format: 6 alphanumeric characters
    CODE_LENGTH = 6
    CODE_CHARSET = string.ascii_uppercase + string.digits
    
    # Rewards
    REFERRER_REWARD = 50000  # 50k sum per successful referral
    REFERRED_BONUS = 10000   # 10k sum bonus for new user
    
    # Limits
    MAX_REFERRALS_PER_DAY = 10
    MAX_TOTAL_REFERRALS = 100
    
    @classmethod
    def generate_referral_code(cls) -> str:
        """
        Generate unique referral code
        
        Returns:
            6-character alphanumeric code
        """
        return ''.join(random.choices(cls.CODE_CHARSET, k=cls.CODE_LENGTH))
    
    @classmethod
    async def create_referral_code(
        cls,
        db: AsyncSession,
        user_id: str
    ) -> str:
        """
        Create unique referral code for user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Generated referral code
        """
        # Check if user already has a code
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        
        if user.referral_code:
            return user.referral_code
        
        # Generate unique code
        max_attempts = 10
        for _ in range(max_attempts):
            code = cls.generate_referral_code()
            
            # Check if code already exists
            existing = await db.execute(
                select(User).where(User.referral_code == code)
            )
            if not existing.scalars().first():
                # Code is unique
                user.referral_code = code
                await db.commit()
                return code
        
        raise ValueError("Could not generate unique referral code")
    
    @classmethod
    async def validate_referral_code(
        cls,
        db: AsyncSession,
        code: str
    ) -> Optional[User]:
        """
        Validate referral code and get referrer
        
        Args:
            db: Database session
            code: Referral code
            
        Returns:
            Referrer user or None
        """
        if not code or len(code) != cls.CODE_LENGTH:
            return None
        
        # Find user with this referral code
        result = await db.execute(
            select(User).where(
                and_(
                    User.referral_code == code.upper(),
                    User.is_active == True
                )
            )
        )
        return result.scalars().first()
    
    @classmethod
    async def apply_referral(
        cls,
        db: AsyncSession,
        referred_user_id: str,
        referral_code: str
    ) -> bool:
        """
        Apply referral code to new user
        
        Args:
            db: Database session
            referred_user_id: New user ID
            referral_code: Referral code
            
        Returns:
            True if applied successfully
        """
        # Get referred user
        referred_user = await db.get(User, referred_user_id)
        if not referred_user:
            return False
        
        # Check if already has referrer
        if referred_user.referred_by_id:
            return False
        
        # Validate referral code
        referrer = await cls.validate_referral_code(db, referral_code)
        if not referrer:
            return False
        
        # Cannot refer yourself
        if referrer.id == referred_user_id:
            return False
        
        # Check daily limit
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_count = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.referred_by_id == referrer.id,
                    User.created_at >= today_start
                )
            )
        )
        if daily_count.scalar() >= cls.MAX_REFERRALS_PER_DAY:
            return False
        
        # Check total limit
        total_count = await db.execute(
            select(func.count(User.id)).where(User.referred_by_id == referrer.id)
        )
        if total_count.scalar() >= cls.MAX_TOTAL_REFERRALS:
            return False
        
        # Apply referral
        referred_user.referred_by_id = referrer.id
        await db.commit()
        return True
    
    @classmethod
    async def get_referral_stats(
        cls,
        db: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get referral statistics for user
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Referral statistics
        """
        user = await db.get(User, user_id, options=[selectinload(User.referred_users)])
        if not user:
            raise ValueError("User not found")
        
        # Count total referrals
        total_referrals = len(user.referred_users)
        
        # Count active referrals (users who completed at least one loan)
        active_referrals = 0
        pending_rewards = 0
        earned_rewards = 0
        
        for referred in user.referred_users:
            # Check if referred user has completed loan
            completed_apps = await db.execute(
                select(func.count(Application.id)).where(
                    and_(
                        Application.user_id == referred.id,
                        Application.status == ApplicationStatus.COMPLETED
                    )
                )
            )
            if completed_apps.scalar() > 0:
                active_referrals += 1
                earned_rewards += cls.REFERRER_REWARD
            else:
                pending_rewards += cls.REFERRER_REWARD
        
        # Get recent referrals
        recent_referrals = await db.execute(
            select(User).where(
                and_(
                    User.referred_by_id == user_id,
                    User.created_at >= datetime.now() - timedelta(days=30)
                )
            ).order_by(User.created_at.desc()).limit(10)
        )
        
        recent_list = []
        for referred in recent_referrals.scalars():
            recent_list.append({
                "id": referred.id,
                "phone": referred.phone_number[-4:],  # Last 4 digits
                "joined_at": referred.created_at.isoformat(),
                "is_active": referred.is_active
            })
        
        return {
            "referral_code": user.referral_code,
            "total_referrals": total_referrals,
            "active_referrals": active_referrals,
            "earned_rewards": earned_rewards,
            "pending_rewards": pending_rewards,
            "daily_limit_remaining": cls.MAX_REFERRALS_PER_DAY - await cls._get_daily_count(db, user_id),
            "total_limit_remaining": cls.MAX_TOTAL_REFERRALS - total_referrals,
            "recent_referrals": recent_list,
            "referral_link": cls.generate_referral_link(user.referral_code) if user.referral_code else None
        }
    
    @classmethod
    async def _get_daily_count(cls, db: AsyncSession, user_id: str) -> int:
        """Get number of referrals today"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.referred_by_id == user_id,
                    User.created_at >= today_start
                )
            )
        )
        return result.scalar() or 0
    
    @classmethod
    def generate_referral_link(cls, code: str) -> str:
        """Generate referral link"""
        # In production, use actual domain
        base_url = "https://kreditomat.uz"
        return f"{base_url}/?ref={code}"
    
    @classmethod
    async def get_referral_tree(
        cls,
        db: AsyncSession,
        user_id: str,
        max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Get referral tree for user
        
        Args:
            db: Database session
            user_id: User ID
            max_depth: Maximum tree depth
            
        Returns:
            Referral tree structure
        """
        async def build_tree(user_id: str, depth: int = 0) -> Optional[Dict[str, Any]]:
            if depth >= max_depth:
                return None
            
            user = await db.get(User, user_id, options=[selectinload(User.referred_users)])
            if not user:
                return None
            
            # Get user's referrals
            referrals = []
            for referred in user.referred_users:
                # Get referred user's stats
                apps_count = await db.execute(
                    select(func.count(Application.id)).where(
                        Application.user_id == referred.id
                    )
                )
                
                referred_data = {
                    "id": referred.id,
                    "phone": referred.phone_number[-4:],
                    "joined_at": referred.created_at.isoformat(),
                    "applications_count": apps_count.scalar() or 0,
                    "referrals": []
                }
                
                # Recursively get sub-referrals
                if depth + 1 < max_depth:
                    sub_tree = await build_tree(referred.id, depth + 1)
                    if sub_tree and sub_tree.get("referrals"):
                        referred_data["referrals"] = sub_tree["referrals"]
                
                referrals.append(referred_data)
            
            return {
                "id": user.id,
                "phone": user.phone_number[-4:],
                "referral_code": user.referral_code,
                "referrals": referrals
            }
        
        return await build_tree(user_id) or {}
    
    @classmethod
    async def calculate_network_value(
        cls,
        db: AsyncSession,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Calculate total value of user's referral network
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Network value metrics
        """
        # Get all users in network (up to 3 levels deep)
        network_users = set()
        
        async def collect_network(user_id: str, depth: int = 0):
            if depth >= 3 or user_id in network_users:
                return
            
            network_users.add(user_id)
            
            # Get direct referrals
            result = await db.execute(
                select(User.id).where(User.referred_by_id == user_id)
            )
            for (referred_id,) in result:
                await collect_network(referred_id, depth + 1)
        
        await collect_network(user_id)
        network_users.discard(user_id)  # Remove self
        
        # Calculate metrics
        total_network_size = len(network_users)
        
        # Total loans in network
        total_loans = await db.execute(
            select(
                func.count(Application.id),
                func.sum(Application.amount)
            ).where(
                and_(
                    Application.user_id.in_(network_users),
                    Application.status.in_([
                        ApplicationStatus.APPROVED,
                        ApplicationStatus.COMPLETED
                    ])
                )
            )
        )
        loan_count, loan_sum = total_loans.first()
        
        # Average network activity
        active_users = await db.execute(
            select(func.count(func.distinct(Application.user_id))).where(
                and_(
                    Application.user_id.in_(network_users),
                    Application.created_at >= datetime.now() - timedelta(days=30)
                )
            )
        )
        active_count = active_users.scalar() or 0
        
        return {
            "network_size": total_network_size,
            "total_loans": loan_count or 0,
            "total_loan_volume": float(loan_sum or 0),
            "active_users_30d": active_count,
            "activity_rate": (active_count / total_network_size * 100) if total_network_size > 0 else 0,
            "estimated_lifetime_value": total_network_size * cls.REFERRER_REWARD
        }
    
    @classmethod
    async def get_top_referrers(
        cls,
        db: AsyncSession,
        limit: int = 10,
        period_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get top referrers by number of active referrals
        
        Args:
            db: Database session
            limit: Number of top referrers to return
            period_days: Period to consider (0 for all time)
            
        Returns:
            List of top referrers
        """
        # Build query for referral counts
        query = select(
            User.id,
            User.phone_number,
            User.referral_code,
            func.count(User.id).label("referral_count")
        ).select_from(User).join(
            User.referred_users
        ).group_by(
            User.id, User.phone_number, User.referral_code
        )
        
        # Add period filter if specified
        if period_days > 0:
            period_start = datetime.now() - timedelta(days=period_days)
            query = query.where(User.created_at >= period_start)
        
        # Order by referral count and limit
        query = query.order_by(func.count(User.id).desc()).limit(limit)
        
        result = await db.execute(query)
        
        top_referrers = []
        for row in result:
            # Calculate earnings for this referrer
            earnings_result = await db.execute(
                select(func.count(Application.id)).select_from(User).join(
                    Application, User.id == Application.user_id
                ).where(
                    and_(
                        User.referred_by_id == row.id,
                        Application.status == ApplicationStatus.COMPLETED
                    )
                )
            )
            completed_referrals = earnings_result.scalar() or 0
            
            top_referrers.append({
                "user_id": row.id,
                "phone": row.phone_number[-4:],  # Last 4 digits
                "referral_code": row.referral_code,
                "total_referrals": row.referral_count,
                "completed_referrals": completed_referrals,
                "total_earnings": completed_referrals * cls.REFERRER_REWARD
            })
        
        return top_referrers