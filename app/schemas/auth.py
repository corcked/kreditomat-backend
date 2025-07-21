from pydantic import BaseModel, Field, validator
import re
from typing import Optional


class PhoneRequest(BaseModel):
    """Schema for phone number request"""
    phone: str = Field(
        ..., 
        description="Phone number in international format",
        example="+998901234567"
    )
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate Uzbek phone number format"""
        # Remove spaces and dashes
        v = v.replace(" ", "").replace("-", "")
        
        # Check if it's a valid Uzbek phone number
        if not re.match(r'^\+998\d{9}$', v):
            raise ValueError(
                "Invalid phone number format. "
                "Please use Uzbek format: +998XXXXXXXXX"
            )
        return v


class VerifyRequest(BaseModel):
    """Schema for verification request"""
    phone: str = Field(
        ..., 
        description="Phone number in international format",
        example="+998901234567"
    )
    code: str = Field(
        ..., 
        description="6-digit verification code",
        example="123456"
    )
    
    @validator('phone')
    def validate_phone(cls, v):
        """Validate Uzbek phone number format"""
        v = v.replace(" ", "").replace("-", "")
        if not re.match(r'^\+998\d{9}$', v):
            raise ValueError("Invalid phone number format")
        return v
    
    @validator('code')
    def validate_code(cls, v):
        """Validate OTP code format"""
        if not re.match(r'^\d{6}$', v):
            raise ValueError("Code must be exactly 6 digits")
        return v


class AuthResponse(BaseModel):
    """Schema for authentication response"""
    access_token: str = Field(
        ..., 
        description="JWT access token"
    )
    token_type: str = Field(
        default="bearer",
        description="Token type"
    )
    user_id: str = Field(
        ..., 
        description="User ID"
    )
    expires_in: int = Field(
        ..., 
        description="Token expiration time in seconds"
    )
    is_new_user: bool = Field(
        default=False,
        description="Whether this is a new user"
    )


class MessageResponse(BaseModel):
    """Schema for simple message responses"""
    success: bool = Field(
        ..., 
        description="Operation success status"
    )
    message: str = Field(
        ..., 
        description="Response message"
    )
    code: Optional[str] = Field(
        None, 
        description="OTP code (only in dev mode)"
    )
    
    
class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str = Field(
        ..., 
        description="Error details"
    )
    

class TokenData(BaseModel):
    """Schema for token payload data"""
    sub: str = Field(
        ..., 
        description="Subject (user ID)"
    )
    phone: str = Field(
        ..., 
        description="User phone number"
    )