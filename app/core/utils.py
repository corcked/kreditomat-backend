import random
import string
from typing import Optional
from sqlalchemy.orm import Session
from app.models import User


def generate_unique_referral_code(db: Session, length: int = 8) -> str:
    """
    Generate unique referral code
    
    Args:
        db: Database session
        length: Code length
        
    Returns:
        Unique referral code
    """
    max_attempts = 100
    
    for _ in range(max_attempts):
        # Generate random code
        code = ''.join(random.choices(
            string.ascii_uppercase + string.digits, 
            k=length
        ))
        
        # Check if code already exists
        existing = db.query(User).filter(User.referral_code == code).first()
        if not existing:
            return code
    
    # If we couldn't generate unique code, raise error
    raise ValueError("Failed to generate unique referral code")


def format_phone_number(phone: str) -> str:
    """
    Format phone number to standard format
    
    Args:
        phone: Phone number
        
    Returns:
        Formatted phone number
    """
    # Remove all non-digit characters except +
    phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Ensure it starts with +
    if not phone.startswith('+'):
        phone = '+' + phone
        
    return phone


def mask_phone_number(phone: str) -> str:
    """
    Mask phone number for display
    
    Args:
        phone: Phone number
        
    Returns:
        Masked phone number (e.g., +998 90 *** ** 67)
    """
    if len(phone) < 7:
        return phone
        
    # Keep country code and first 2 digits, last 2 digits
    masked = phone[:7] + '***' + phone[-2:]
    
    # Format for display
    if phone.startswith('+998'):
        return f"{phone[:4]} {phone[4:6]} *** ** {phone[-2:]}"
    
    return masked