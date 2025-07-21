from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from app.services.calculator import calculate_monthly_payment, validate_loan_params
from app.core.config import get_settings

settings = get_settings()


class PDNRiskLevel(str, Enum):
    """PDN risk levels"""
    LOW = "low"  # < 30%
    MEDIUM = "medium"  # 30-50%
    HIGH = "high"  # 50-65%
    CRITICAL = "critical"  # > 65%


def calculate_pdn(
    monthly_payment: Decimal,
    monthly_income: Decimal,
    other_monthly_payments: Decimal = Decimal("0")
) -> Decimal:
    """
    Calculate Payment-to-Debt Ratio (PDN)
    
    Args:
        monthly_payment: New loan monthly payment
        monthly_income: Total monthly income
        other_monthly_payments: Other existing monthly payments
        
    Returns:
        PDN as percentage
        
    Formula: PDN = ((monthly_payment + other_payments) / income) * 100
    """
    if monthly_income <= 0:
        raise ValueError("Monthly income must be positive")
    
    total_payments = monthly_payment + other_monthly_payments
    pdn = (total_payments / monthly_income * 100).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    
    return pdn


def get_pdn_risk_level(pdn: Decimal) -> PDNRiskLevel:
    """
    Determine PDN risk level
    
    Args:
        pdn: PDN percentage
        
    Returns:
        Risk level enum
    """
    if pdn < 30:
        return PDNRiskLevel.LOW
    elif pdn < 50:
        return PDNRiskLevel.MEDIUM
    elif pdn < 65:
        return PDNRiskLevel.HIGH
    else:
        return PDNRiskLevel.CRITICAL


def auto_correct_loan_params(
    amount: Decimal,
    annual_rate: Decimal,
    months: int,
    monthly_income: Decimal,
    other_monthly_payments: Decimal = Decimal("0"),
    target_pdn: Decimal = Decimal("50")
) -> Dict[str, Any]:
    """
    Auto-correct loan parameters to achieve target PDN
    
    Args:
        amount: Requested loan amount
        annual_rate: Annual interest rate
        months: Requested loan term in months
        monthly_income: Monthly income
        other_monthly_payments: Other monthly payments
        target_pdn: Target PDN percentage (default 50%)
        
    Returns:
        Dictionary with corrected parameters and correction details
        
    Algorithm:
    1. Calculate current PDN
    2. If PDN > target, extend term to 36 months
    3. If still > target, reduce amount
    """
    # Validate initial parameters
    validation = validate_loan_params(amount, months)
    if not validation["valid"]:
        raise ValueError(f"Invalid loan parameters: {', '.join(validation['errors'])}")
    
    # Calculate initial monthly payment and PDN
    monthly_payment = calculate_monthly_payment(amount, annual_rate, months)
    current_pdn = calculate_pdn(monthly_payment, monthly_income, other_monthly_payments)
    
    # Track corrections made
    corrections = []
    corrected_amount = amount
    corrected_months = months
    
    # If PDN is already acceptable, return original parameters
    if current_pdn <= target_pdn:
        return {
            "amount": amount,
            "months": months,
            "monthly_payment": monthly_payment,
            "pdn": current_pdn,
            "risk_level": get_pdn_risk_level(current_pdn),
            "corrected": False,
            "corrections": []
        }
    
    # Step 1: Try extending term to 36 months if current term is less
    if months < 36:
        corrected_months = 36
        monthly_payment = calculate_monthly_payment(amount, annual_rate, corrected_months)
        current_pdn = calculate_pdn(monthly_payment, monthly_income, other_monthly_payments)
        corrections.append({
            "type": "term_extended",
            "from": months,
            "to": corrected_months,
            "reason": "PDN exceeds target"
        })
        
        # If PDN is now acceptable, return
        if current_pdn <= target_pdn:
            return {
                "amount": corrected_amount,
                "months": corrected_months,
                "monthly_payment": monthly_payment,
                "pdn": current_pdn,
                "risk_level": get_pdn_risk_level(current_pdn),
                "corrected": True,
                "corrections": corrections
            }
    
    # Step 2: Reduce amount to achieve target PDN
    # Calculate maximum affordable monthly payment
    max_monthly_payment = (monthly_income * target_pdn / 100) - other_monthly_payments
    
    if max_monthly_payment <= 0:
        raise ValueError("Cannot afford any loan with current income and obligations")
    
    # Binary search for maximum affordable amount
    min_amount = settings.MIN_LOAN_AMOUNT
    max_amount = corrected_amount
    
    while max_amount - min_amount > Decimal("100000"):  # 100k sum precision
        mid_amount = ((min_amount + max_amount) / 2).quantize(
            Decimal('100000'), rounding=ROUND_HALF_UP
        )
        
        mid_payment = calculate_monthly_payment(mid_amount, annual_rate, corrected_months)
        mid_pdn = calculate_pdn(mid_payment, monthly_income, other_monthly_payments)
        
        if mid_pdn <= target_pdn:
            min_amount = mid_amount
        else:
            max_amount = mid_amount
    
    # Use the lower amount to ensure we stay under target PDN
    corrected_amount = min_amount
    monthly_payment = calculate_monthly_payment(corrected_amount, annual_rate, corrected_months)
    current_pdn = calculate_pdn(monthly_payment, monthly_income, other_monthly_payments)
    
    corrections.append({
        "type": "amount_reduced",
        "from": amount,
        "to": corrected_amount,
        "reason": "PDN exceeds target even with extended term"
    })
    
    return {
        "amount": corrected_amount,
        "months": corrected_months,
        "monthly_payment": monthly_payment,
        "pdn": current_pdn,
        "risk_level": get_pdn_risk_level(current_pdn),
        "corrected": True,
        "corrections": corrections
    }


def calculate_max_loan_amount(
    annual_rate: Decimal,
    months: int,
    monthly_income: Decimal,
    other_monthly_payments: Decimal = Decimal("0"),
    target_pdn: Decimal = Decimal("50")
) -> Decimal:
    """
    Calculate maximum loan amount for given income and target PDN
    
    Args:
        annual_rate: Annual interest rate
        months: Loan term in months
        monthly_income: Monthly income
        other_monthly_payments: Other monthly payments
        target_pdn: Target PDN percentage
        
    Returns:
        Maximum loan amount
    """
    # Calculate maximum affordable monthly payment
    max_monthly_payment = (monthly_income * target_pdn / 100) - other_monthly_payments
    
    if max_monthly_payment <= 0:
        return Decimal("0")
    
    # Use annuity formula to calculate principal
    # PMT = P * (r * (1 + r)^n) / ((1 + r)^n - 1)
    # P = PMT * ((1 + r)^n - 1) / (r * (1 + r)^n)
    
    monthly_rate = (annual_rate / 100) / 12
    
    if monthly_rate == 0:
        # No interest case
        max_amount = max_monthly_payment * months
    else:
        rate_power = (1 + monthly_rate) ** months
        max_amount = max_monthly_payment * (rate_power - 1) / (monthly_rate * rate_power)
    
    # Round down to nearest 100k and ensure within limits
    max_amount = max_amount.quantize(Decimal('100000'), rounding=ROUND_HALF_UP)
    max_amount = min(max_amount, settings.MAX_LOAN_AMOUNT)
    max_amount = max(max_amount, settings.MIN_LOAN_AMOUNT)
    
    return max_amount


def analyze_pdn_scenario(
    amount: Decimal,
    annual_rate: Decimal,
    months: int,
    monthly_income: Decimal,
    other_monthly_payments: Decimal = Decimal("0")
) -> Dict[str, Any]:
    """
    Analyze PDN scenario with recommendations
    
    Args:
        amount: Loan amount
        annual_rate: Annual interest rate
        months: Loan term
        monthly_income: Monthly income
        other_monthly_payments: Other monthly payments
        
    Returns:
        Analysis with current PDN, recommendations, and alternatives
    """
    # Calculate current scenario
    monthly_payment = calculate_monthly_payment(amount, annual_rate, months)
    current_pdn = calculate_pdn(monthly_payment, monthly_income, other_monthly_payments)
    risk_level = get_pdn_risk_level(current_pdn)
    
    # Calculate alternative scenarios
    alternatives = []
    
    # Alternative 1: Extended term (if possible)
    if months < 36:
        alt_payment = calculate_monthly_payment(amount, annual_rate, 36)
        alt_pdn = calculate_pdn(alt_payment, monthly_income, other_monthly_payments)
        alternatives.append({
            "description": "Увеличить срок до 36 месяцев",
            "amount": amount,
            "months": 36,
            "monthly_payment": alt_payment,
            "pdn": alt_pdn,
            "risk_level": get_pdn_risk_level(alt_pdn).value,
            "benefit": "Снижение ежемесячного платежа"
        })
    
    # Alternative 2: Reduced amount
    if amount > settings.MIN_LOAN_AMOUNT:
        reduced_amount = amount * Decimal("0.75")  # 75% of requested
        reduced_amount = reduced_amount.quantize(Decimal('100000'), rounding=ROUND_HALF_UP)
        reduced_amount = max(reduced_amount, settings.MIN_LOAN_AMOUNT)
        
        alt_payment = calculate_monthly_payment(reduced_amount, annual_rate, months)
        alt_pdn = calculate_pdn(alt_payment, monthly_income, other_monthly_payments)
        alternatives.append({
            "description": "Уменьшить сумму займа",
            "amount": reduced_amount,
            "months": months,
            "monthly_payment": alt_payment,
            "pdn": alt_pdn,
            "risk_level": get_pdn_risk_level(alt_pdn).value,
            "benefit": "Снижение долговой нагрузки"
        })
    
    # Calculate maximum affordable amount
    max_amount = calculate_max_loan_amount(
        annual_rate, months, monthly_income, other_monthly_payments
    )
    
    # Recommendations based on risk level
    recommendations = []
    if risk_level == PDNRiskLevel.LOW:
        recommendations.append("Ваша долговая нагрузка находится в безопасной зоне")
        recommendations.append("Вы можете рассмотреть займы на большую сумму")
    elif risk_level == PDNRiskLevel.MEDIUM:
        recommendations.append("Ваша долговая нагрузка находится в приемлемом диапазоне")
        recommendations.append("Рекомендуем не увеличивать долговую нагрузку")
    elif risk_level == PDNRiskLevel.HIGH:
        recommendations.append("Ваша долговая нагрузка приближается к критической")
        recommendations.append("Рекомендуем уменьшить сумму займа или увеличить срок")
        recommendations.append("Избегайте дополнительных кредитов")
    else:  # CRITICAL
        recommendations.append("Ваша долговая нагрузка превышает безопасный уровень")
        recommendations.append("Настоятельно рекомендуем уменьшить сумму займа")
        recommendations.append("Рассмотрите возможность отказа от займа")
    
    return {
        "current_scenario": {
            "amount": amount,
            "months": months,
            "monthly_payment": monthly_payment,
            "pdn": current_pdn,
            "risk_level": risk_level.value,
            "risk_description": get_risk_description(risk_level)
        },
        "income_analysis": {
            "monthly_income": monthly_income,
            "other_payments": other_monthly_payments,
            "free_income": monthly_income - other_monthly_payments,
            "free_income_percentage": ((monthly_income - other_monthly_payments) / monthly_income * 100).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            ) if monthly_income > 0 else Decimal("0")
        },
        "max_affordable_amount": max_amount,
        "alternatives": alternatives,
        "recommendations": recommendations
    }


def get_risk_description(risk_level: PDNRiskLevel) -> str:
    """Get human-readable risk description"""
    descriptions = {
        PDNRiskLevel.LOW: "Низкий риск - комфортная долговая нагрузка",
        PDNRiskLevel.MEDIUM: "Средний риск - приемлемая долговая нагрузка",
        PDNRiskLevel.HIGH: "Высокий риск - значительная долговая нагрузка",
        PDNRiskLevel.CRITICAL: "Критический риск - чрезмерная долговая нагрузка"
    }
    return descriptions.get(risk_level, "Неизвестный уровень риска")