import redis
from typing import Optional
from app.core.config import get_settings

settings = get_settings()

# Create Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    str(settings.REDIS_URL),
    decode_responses=True,
    max_connections=50
)

# Create Redis client
redis_client = redis.Redis(connection_pool=redis_pool)


class RedisService:
    """Service for Redis operations"""
    
    @staticmethod
    def store_otp(phone: str, code: str, ttl: int = None) -> bool:
        """
        Store OTP code for phone number
        
        Args:
            phone: Phone number
            code: OTP code
            ttl: Time to live in seconds (default from settings)
            
        Returns:
            True if stored successfully
        """
        if ttl is None:
            ttl = settings.OTP_TTL_SECONDS
            
        key = f"otp:{phone}"
        return redis_client.setex(key, ttl, code)
    
    @staticmethod
    def get_otp(phone: str) -> Optional[str]:
        """
        Get OTP code for phone number
        
        Args:
            phone: Phone number
            
        Returns:
            OTP code if exists, None otherwise
        """
        key = f"otp:{phone}"
        return redis_client.get(key)
    
    @staticmethod
    def delete_otp(phone: str) -> bool:
        """
        Delete OTP code for phone number
        
        Args:
            phone: Phone number
            
        Returns:
            True if deleted successfully
        """
        key = f"otp:{phone}"
        return bool(redis_client.delete(key))
    
    @staticmethod
    def store_session(user_id: str, token: str, ttl: int = None) -> bool:
        """
        Store user session
        
        Args:
            user_id: User ID
            token: Session token
            ttl: Time to live in seconds (default from settings)
            
        Returns:
            True if stored successfully
        """
        if ttl is None:
            ttl = settings.SESSION_TTL_SECONDS
            
        key = f"session:{token}"
        return redis_client.setex(key, ttl, user_id)
    
    @staticmethod
    def get_session(token: str) -> Optional[str]:
        """
        Get user ID from session token
        
        Args:
            token: Session token
            
        Returns:
            User ID if session exists, None otherwise
        """
        key = f"session:{token}"
        return redis_client.get(key)
    
    @staticmethod
    def delete_session(token: str) -> bool:
        """
        Delete user session
        
        Args:
            token: Session token
            
        Returns:
            True if deleted successfully
        """
        key = f"session:{token}"
        return bool(redis_client.delete(key))
    
    @staticmethod
    def extend_session(token: str, ttl: int = None) -> bool:
        """
        Extend session TTL
        
        Args:
            token: Session token
            ttl: New time to live in seconds
            
        Returns:
            True if extended successfully
        """
        if ttl is None:
            ttl = settings.SESSION_TTL_SECONDS
            
        key = f"session:{token}"
        return bool(redis_client.expire(key, ttl))
    
    @staticmethod
    def check_rate_limit(identifier: str, limit: int = 5, window: int = 60) -> bool:
        """
        Check rate limit for an identifier
        
        Args:
            identifier: Unique identifier (e.g., IP, phone)
            limit: Maximum number of requests
            window: Time window in seconds
            
        Returns:
            True if within limit, False if exceeded
        """
        key = f"rate_limit:{identifier}"
        
        try:
            current = redis_client.incr(key)
            if current == 1:
                redis_client.expire(key, window)
            return current <= limit
        except Exception:
            return True  # Allow on Redis error
    
    @staticmethod
    def get_rate_limit_remaining(identifier: str, limit: int = 5) -> int:
        """
        Get remaining rate limit count
        
        Args:
            identifier: Unique identifier
            limit: Maximum number of requests
            
        Returns:
            Number of remaining requests
        """
        key = f"rate_limit:{identifier}"
        current = redis_client.get(key)
        if current is None:
            return limit
        return max(0, limit - int(current))