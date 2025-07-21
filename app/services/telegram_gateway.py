import httpx
import random
import string
from typing import Dict, Any, Optional
from app.core.config import get_settings
from app.core.redis import RedisService

settings = get_settings()


class TelegramGatewayService:
    """Service for Telegram Gateway integration"""
    
    def __init__(self):
        self.base_url = settings.TELEGRAM_GATEWAY_URL
        self.token = settings.TELEGRAM_GATEWAY_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    @staticmethod
    def generate_otp_code() -> str:
        """Generate random 6-digit OTP code"""
        return ''.join(random.choices(string.digits, k=settings.OTP_LENGTH))
    
    async def send_verification_code(self, phone: str) -> Dict[str, Any]:
        """
        Send verification code via Telegram Gateway
        
        Args:
            phone: Phone number in international format
            
        Returns:
            Response dictionary with status
            
        Raises:
            Exception: If sending fails
        """
        # Check rate limit
        if not RedisService.check_rate_limit(f"otp_send:{phone}", limit=3, window=300):
            raise Exception("Too many OTP requests. Please try again later.")
        
        # Generate OTP code
        code = self.generate_otp_code()
        
        # Store code in Redis
        RedisService.store_otp(phone, code)
        
        # In development mode, just return success without sending
        if settings.ENVIRONMENT == "dev" and not settings.TELEGRAM_GATEWAY_TOKEN:
            return {
                "success": True,
                "message": f"Development mode: OTP code is {code}",
                "code": code  # Only in dev mode!
            }
        
        # Send via Telegram Gateway
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/sendVerificationMessage",
                    headers=self.headers,
                    json={
                        "phone_number": phone,
                        "code": code,
                        "code_length": settings.OTP_LENGTH,
                        "ttl": settings.OTP_TTL_SECONDS
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Verification code sent successfully"
                    }
                else:
                    error_data = response.json()
                    raise Exception(f"Telegram Gateway error: {error_data.get('error', 'Unknown error')}")
                    
            except httpx.TimeoutException:
                raise Exception("Telegram Gateway timeout")
            except httpx.RequestError as e:
                raise Exception(f"Network error: {str(e)}")
    
    def verify_code(self, phone: str, code: str) -> bool:
        """
        Verify OTP code
        
        Args:
            phone: Phone number
            code: OTP code to verify
            
        Returns:
            True if code is valid
        """
        stored_code = RedisService.get_otp(phone)
        
        if not stored_code:
            return False
        
        if stored_code == code:
            # Delete code after successful verification
            RedisService.delete_otp(phone)
            return True
            
        return False
    
    async def check_phone_availability(self, phone: str) -> Dict[str, Any]:
        """
        Check if phone number can receive messages via Telegram
        
        Args:
            phone: Phone number to check
            
        Returns:
            Response dictionary with availability status
        """
        # In development mode, assume all phones are available
        if settings.ENVIRONMENT == "dev" and not settings.TELEGRAM_GATEWAY_TOKEN:
            return {
                "available": True,
                "has_telegram": True
            }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/checkPhoneNumber",
                    headers=self.headers,
                    json={"phone_number": phone},
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "available": data.get("result", False),
                        "has_telegram": data.get("has_telegram", False)
                    }
                else:
                    return {
                        "available": False,
                        "has_telegram": False
                    }
                    
            except Exception:
                # Default to available on error
                return {
                    "available": True,
                    "has_telegram": False
                }


# Global instance
telegram_gateway = TelegramGatewayService()