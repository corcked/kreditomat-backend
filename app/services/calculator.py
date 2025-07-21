from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any

from app.core.config import get_settings

settings = get_settings()


def calculate_monthly_payment(
    amount: Decimal, 
    annual_rate: Decimal, 
    months: int
) -> Decimal:
    """
    Calculate monthly payment using annuity formula
    
    Args:
        amount: Loan amount
        annual_rate: Annual interest rate (percentage)
        months: Loan term in months
        
    Returns:
        Monthly payment amount
        
    Formula: PMT = P * (r * (1 + r)^n) / ((1 + r)^n - 1)
    where:
        P = principal amount
        r = monthly interest rate
        n = number of months
    """
    if months <= 0:
        raise ValueError("Loan term must be positive")
    
    if amount <= 0:
        raise ValueError("Loan amount must be positive")
    
    # Convert annual rate to monthly rate (as decimal)
    monthly_rate = (annual_rate / 100) / 12
    
    if monthly_rate == 0:
        # If no interest, simply divide amount by months
        return (amount / months).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Calculate payment using annuity formula
    rate_power = (1 + monthly_rate) ** months
    monthly_payment = amount * (monthly_rate * rate_power) / (rate_power - 1)
    
    # Round to 2 decimal places
    return monthly_payment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_total_cost(monthly_payment: Decimal, months: int) -> Decimal:
    """
    Calculate total cost of the loan
    
    Args:
        monthly_payment: Monthly payment amount
        months: Loan term in months
        
    Returns:
        Total amount to be paid
    """
    if months <= 0:
        raise ValueError("Loan term must be positive")
    
    if monthly_payment <= 0:
        raise ValueError("Monthly payment must be positive")
    
    return (monthly_payment * months).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_overpayment(amount: Decimal, total_cost: Decimal) -> Decimal:
    """
    Calculate overpayment amount
    
    Args:
        amount: Original loan amount
        total_cost: Total amount to be paid
        
    Returns:
        Overpayment amount
    """
    return (total_cost - amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_effective_rate(
    amount: Decimal,
    total_cost: Decimal,
    months: int
) -> Decimal:
    """
    Calculate effective annual interest rate
    
    Args:
        amount: Loan amount
        total_cost: Total amount to be paid
        months: Loan term in months
        
    Returns:
        Effective annual rate as percentage
    """
    if months <= 0 or amount <= 0:
        return Decimal('0')
    
    # Calculate total interest
    total_interest = total_cost - amount
    
    # Simple calculation of effective rate
    # (Total Interest / Principal) / Years * 100
    years = Decimal(months) / 12
    effective_rate = (total_interest / amount / years * 100)
    
    return effective_rate.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def validate_loan_params(amount: Decimal, months: int) -> Dict[str, Any]:
    """
    Validate loan parameters against system limits
    
    Args:
        amount: Loan amount
        months: Loan term in months
        
    Returns:
        Validation result with status and errors
    """
    errors = []
    
    # Validate amount
    if amount < settings.MIN_LOAN_AMOUNT:
        errors.append(f"Минимальная сумма займа: {settings.MIN_LOAN_AMOUNT} сум")
    elif amount > settings.MAX_LOAN_AMOUNT:
        errors.append(f"Максимальная сумма займа: {settings.MAX_LOAN_AMOUNT} сум")
    
    # Validate term
    if months < settings.MIN_LOAN_TERM_MONTHS:
        errors.append(f"Минимальный срок займа: {settings.MIN_LOAN_TERM_MONTHS} месяцев")
    elif months > settings.MAX_LOAN_TERM_MONTHS:
        errors.append(f"Максимальный срок займа: {settings.MAX_LOAN_TERM_MONTHS} месяцев")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }


def calculate_loan_details(
    amount: Decimal,
    annual_rate: Decimal,
    months: int
) -> Dict[str, Any]:
    """
    Calculate complete loan details
    
    Args:
        amount: Loan amount
        annual_rate: Annual interest rate
        months: Loan term in months
        
    Returns:
        Dictionary with all loan calculations
    """
    # Validate parameters first
    validation = validate_loan_params(amount, months)
    if not validation["valid"]:
        raise ValueError(f"Invalid loan parameters: {', '.join(validation['errors'])}")
    
    # Calculate all values
    monthly_payment = calculate_monthly_payment(amount, annual_rate, months)
    total_cost = calculate_total_cost(monthly_payment, months)
    overpayment = calculate_overpayment(amount, total_cost)
    effective_rate = calculate_effective_rate(amount, total_cost, months)
    
    return {
        "amount": amount,
        "annual_rate": annual_rate,
        "months": months,
        "monthly_payment": monthly_payment,
        "total_cost": total_cost,
        "overpayment": overpayment,
        "overpayment_percentage": (overpayment / amount * 100).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        ) if amount > 0 else Decimal('0'),
        "effective_rate": effective_rate,
        "daily_rate": (annual_rate / 365).quantize(
            Decimal('0.0001'), rounding=ROUND_HALF_UP
        )
    }


def format_amount(amount: Decimal) -> str:
    """
    Format amount for display with thousands separator
    
    Args:
        amount: Amount to format
        
    Returns:
        Formatted string
    """
    # Convert to string and split by decimal point
    parts = str(amount).split('.')
    
    # Add thousands separator to integer part
    integer_part = parts[0]
    formatted = ""
    for i, digit in enumerate(reversed(integer_part)):
        if i > 0 and i % 3 == 0:
            formatted = " " + formatted
        formatted = digit + formatted
    
    # Add decimal part if exists
    if len(parts) > 1 and parts[1] != '00':
        formatted += '.' + parts[1]
    
    return formatted + " сум"