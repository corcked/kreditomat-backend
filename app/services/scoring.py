from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from app.models.personal_data import (
    Gender, MaritalStatus, EducationLevel, EmploymentType, 
    IncomeSource, LivingArrangement
)
from app.services.pdn import PDNRiskLevel


class ScoreCategory(str, Enum):
    """Scoring categories"""
    EXCELLENT = "excellent"  # 800-900
    GOOD = "good"  # 700-799
    FAIR = "fair"  # 600-699
    POOR = "poor"  # 500-599
    VERY_POOR = "very_poor"  # < 500


class ScoringFactor(str, Enum):
    """Factors affecting credit score"""
    AGE = "age"
    GENDER = "gender"
    MARITAL_STATUS = "marital_status"
    EDUCATION = "education"
    EMPLOYMENT = "employment"
    INCOME = "income"
    LIVING_ARRANGEMENT = "living_arrangement"
    PDN = "pdn"
    LOAN_HISTORY = "loan_history"
    REFERRAL = "referral"
    DEVICE_TYPE = "device_type"
    REGION = "region"


def calculate_age_score(birth_date: date) -> Dict[str, Any]:
    """
    Calculate score based on age
    
    Age scoring:
    - 18-21: 50 points (high risk)
    - 22-25: 80 points
    - 26-35: 100 points (optimal)
    - 36-45: 90 points
    - 46-55: 80 points
    - 56-65: 60 points
    - >65: 40 points (retirement risk)
    """
    today = date.today()
    age = relativedelta(today, birth_date).years
    
    if age < 18:
        return {"score": 0, "reason": "Возраст менее 18 лет", "age": age}
    elif age <= 21:
        return {"score": 50, "reason": "Молодой возраст (высокий риск)", "age": age}
    elif age <= 25:
        return {"score": 80, "reason": "Начало карьеры", "age": age}
    elif age <= 35:
        return {"score": 100, "reason": "Оптимальный возраст", "age": age}
    elif age <= 45:
        return {"score": 90, "reason": "Стабильный возраст", "age": age}
    elif age <= 55:
        return {"score": 80, "reason": "Зрелый возраст", "age": age}
    elif age <= 65:
        return {"score": 60, "reason": "Предпенсионный возраст", "age": age}
    else:
        return {"score": 40, "reason": "Пенсионный возраст", "age": age}


def calculate_gender_score(gender: Gender) -> Dict[str, Any]:
    """
    Calculate score based on gender
    
    Gender scoring (based on statistical risk):
    - Female: 60 points
    - Male: 50 points
    """
    if gender == Gender.FEMALE:
        return {"score": 60, "reason": "Статистически ниже риск"}
    else:
        return {"score": 50, "reason": "Стандартный уровень риска"}


def calculate_marital_status_score(status: MaritalStatus) -> Dict[str, Any]:
    """
    Calculate score based on marital status
    
    Marital status scoring:
    - Married: 80 points (stability)
    - Single: 60 points
    - Divorced: 50 points
    - Widowed: 55 points
    """
    scores = {
        MaritalStatus.MARRIED: {"score": 80, "reason": "Семейная стабильность"},
        MaritalStatus.SINGLE: {"score": 60, "reason": "Одинокий статус"},
        MaritalStatus.DIVORCED: {"score": 50, "reason": "Развод может влиять на финансы"},
        MaritalStatus.WIDOWED: {"score": 55, "reason": "Особые обстоятельства"}
    }
    return scores.get(status, {"score": 60, "reason": "Неизвестный статус"})


def calculate_education_score(education: EducationLevel) -> Dict[str, Any]:
    """
    Calculate score based on education level
    
    Education scoring:
    - Higher: 90 points
    - Secondary: 60 points
    - Basic: 40 points
    """
    scores = {
        EducationLevel.HIGHER: {"score": 90, "reason": "Высшее образование"},
        EducationLevel.SECONDARY: {"score": 60, "reason": "Среднее образование"},
        EducationLevel.BASIC: {"score": 40, "reason": "Базовое образование"}
    }
    return scores.get(education, {"score": 50, "reason": "Неизвестное образование"})


def calculate_employment_score(
    employment_type: EmploymentType,
    employment_duration_months: int
) -> Dict[str, Any]:
    """
    Calculate score based on employment
    
    Employment type scoring:
    - Full-time: 100 points
    - Contract: 70 points
    - Part-time: 60 points
    - Self-employed: 65 points
    - Unemployed: 20 points
    
    Duration bonus:
    - <6 months: -20 points
    - 6-12 months: 0 points
    - 1-3 years: +10 points
    - >3 years: +20 points
    """
    type_scores = {
        EmploymentType.EMPLOYED: 100,
        EmploymentType.SELF_EMPLOYED: 65,
        EmploymentType.UNEMPLOYED: 20,
        EmploymentType.RETIRED: 50,
        EmploymentType.STUDENT: 30
    }
    
    base_score = type_scores.get(employment_type, 50)
    
    # Duration bonus
    if employment_duration_months < 6:
        duration_bonus = -20
        duration_reason = "Менее 6 месяцев на работе"
    elif employment_duration_months < 12:
        duration_bonus = 0
        duration_reason = "Менее года на работе"
    elif employment_duration_months < 36:
        duration_bonus = 10
        duration_reason = "1-3 года на работе"
    else:
        duration_bonus = 20
        duration_reason = "Более 3 лет на работе"
    
    total_score = max(0, base_score + duration_bonus)
    
    return {
        "score": total_score,
        "base_score": base_score,
        "duration_bonus": duration_bonus,
        "reason": f"{employment_type.value}, {duration_reason}"
    }


def calculate_income_score(
    monthly_income: Decimal,
    income_source: IncomeSource
) -> Dict[str, Any]:
    """
    Calculate score based on income level and source
    
    Income level scoring:
    - <500k: 30 points
    - 500k-1M: 50 points
    - 1M-2M: 70 points
    - 2M-5M: 90 points
    - >5M: 100 points
    
    Income source modifier:
    - Salary: x1.0
    - Business: x0.9
    - Pension: x0.8
    - Other: x0.7
    """
    # Base score by income level
    if monthly_income < 500000:
        base_score = 30
        level = "Низкий доход"
    elif monthly_income < 1000000:
        base_score = 50
        level = "Ниже среднего"
    elif monthly_income < 2000000:
        base_score = 70
        level = "Средний доход"
    elif monthly_income < 5000000:
        base_score = 90
        level = "Выше среднего"
    else:
        base_score = 100
        level = "Высокий доход"
    
    # Source modifier
    source_modifiers = {
        IncomeSource.SALARY: 1.0,
        IncomeSource.BUSINESS: 0.9,
        IncomeSource.PENSION: 0.8,
        IncomeSource.OTHER: 0.7
    }
    
    modifier = source_modifiers.get(income_source, 0.7)
    final_score = int(base_score * modifier)
    
    return {
        "score": final_score,
        "base_score": base_score,
        "modifier": modifier,
        "income_level": level,
        "income_source": income_source.value,
        "reason": f"{level} от {income_source.value}"
    }


def calculate_living_score(living: LivingArrangement) -> Dict[str, Any]:
    """
    Calculate score based on living arrangement
    
    Living arrangement scoring:
    - Own: 80 points (asset ownership)
    - Family: 70 points (stability)
    - Rent: 50 points (additional expenses)
    - Other: 40 points
    """
    scores = {
        LivingArrangement.OWN: {"score": 80, "reason": "Собственное жилье"},
        LivingArrangement.FAMILY: {"score": 70, "reason": "Живет с семьей"},
        LivingArrangement.RENT: {"score": 50, "reason": "Арендует жилье"},
        LivingArrangement.OTHER: {"score": 40, "reason": "Другие условия"}
    }
    return scores.get(living, {"score": 50, "reason": "Неизвестные условия"})


def calculate_pdn_score(pdn_risk_level: PDNRiskLevel) -> Dict[str, Any]:
    """
    Calculate score based on PDN risk level
    
    PDN scoring:
    - Low: 100 points
    - Medium: 70 points
    - High: 40 points
    - Critical: 10 points
    """
    scores = {
        PDNRiskLevel.LOW: {"score": 100, "reason": "Низкая долговая нагрузка"},
        PDNRiskLevel.MEDIUM: {"score": 70, "reason": "Средняя долговая нагрузка"},
        PDNRiskLevel.HIGH: {"score": 40, "reason": "Высокая долговая нагрузка"},
        PDNRiskLevel.CRITICAL: {"score": 10, "reason": "Критическая долговая нагрузка"}
    }
    return scores.get(pdn_risk_level, {"score": 50, "reason": "Неизвестный уровень ПДН"})


def calculate_loan_history_score(
    total_loans: int,
    active_loans: int,
    overdue_loans: int
) -> Dict[str, Any]:
    """
    Calculate score based on loan history
    
    Loan history scoring:
    - No loans: 60 points (neutral)
    - 1-3 loans, no overdue: 80 points
    - 4-6 loans, no overdue: 70 points
    - >6 loans: 50 points
    - Any overdue: -30 points per overdue
    """
    if total_loans == 0:
        return {"score": 60, "reason": "Нет кредитной истории"}
    
    # Base score
    if total_loans <= 3:
        base_score = 80
    elif total_loans <= 6:
        base_score = 70
    else:
        base_score = 50
    
    # Penalty for overdue
    overdue_penalty = overdue_loans * 30
    
    # Penalty for too many active loans
    active_penalty = max(0, (active_loans - 2) * 10)
    
    final_score = max(10, base_score - overdue_penalty - active_penalty)
    
    return {
        "score": final_score,
        "total_loans": total_loans,
        "active_loans": active_loans,
        "overdue_loans": overdue_loans,
        "reason": f"Займов: {total_loans}, активных: {active_loans}, просроченных: {overdue_loans}"
    }


def calculate_device_score(device_type: str) -> Dict[str, Any]:
    """
    Calculate score based on device type
    
    Device scoring:
    - Desktop: 70 points (stable)
    - iOS: 80 points (premium)
    - Android: 60 points (standard)
    - Other: 50 points
    """
    device_type_lower = device_type.lower()
    
    if "ios" in device_type_lower or "iphone" in device_type_lower or "ipad" in device_type_lower:
        return {"score": 80, "reason": "Премиум устройство"}
    elif "android" in device_type_lower:
        return {"score": 60, "reason": "Стандартное устройство"}
    elif "windows" in device_type_lower or "mac" in device_type_lower or "desktop" in device_type_lower:
        return {"score": 70, "reason": "Десктоп устройство"}
    else:
        return {"score": 50, "reason": "Неизвестное устройство"}


def calculate_region_score(region: str) -> Dict[str, Any]:
    """
    Calculate score based on region
    
    Region scoring (simplified):
    - Tashkent: 80 points (capital)
    - Regional centers: 60 points
    - Other: 50 points
    """
    region_lower = region.lower()
    
    if "ташкент" in region_lower or "tashkent" in region_lower:
        return {"score": 80, "reason": "Столица"}
    elif any(city in region_lower for city in ["самарканд", "бухара", "наманган", "андижан", "фергана"]):
        return {"score": 60, "reason": "Региональный центр"}
    else:
        return {"score": 50, "reason": "Другой регион"}


def calculate_total_score(
    personal_data: Dict[str, Any],
    pdn_risk_level: PDNRiskLevel,
    loan_history: Optional[Dict[str, Any]] = None,
    device_info: Optional[Dict[str, Any]] = None,
    has_referral: bool = False
) -> Dict[str, Any]:
    """
    Calculate total credit score based on all factors
    
    Args:
        personal_data: Personal information
        pdn_risk_level: Current PDN risk level
        loan_history: Loan history information
        device_info: Device and location information
        has_referral: Whether user came through referral
        
    Returns:
        Complete scoring result with breakdown
    """
    factors = []
    total_weighted_score = 0
    total_weight = 0
    
    # Age score (weight: 15%)
    if "birth_date" in personal_data:
        age_result = calculate_age_score(personal_data["birth_date"])
        factors.append({
            "factor": ScoringFactor.AGE.value,
            "score": age_result["score"],
            "weight": 15,
            "weighted_score": age_result["score"] * 0.15,
            "details": age_result
        })
        total_weighted_score += age_result["score"] * 0.15
        total_weight += 15
    
    # Gender score (weight: 5%)
    if "gender" in personal_data:
        gender_result = calculate_gender_score(personal_data["gender"])
        factors.append({
            "factor": ScoringFactor.GENDER.value,
            "score": gender_result["score"],
            "weight": 5,
            "weighted_score": gender_result["score"] * 0.05,
            "details": gender_result
        })
        total_weighted_score += gender_result["score"] * 0.05
        total_weight += 5
    
    # Marital status score (weight: 5%)
    if "marital_status" in personal_data:
        marital_result = calculate_marital_status_score(personal_data["marital_status"])
        factors.append({
            "factor": ScoringFactor.MARITAL_STATUS.value,
            "score": marital_result["score"],
            "weight": 5,
            "weighted_score": marital_result["score"] * 0.05,
            "details": marital_result
        })
        total_weighted_score += marital_result["score"] * 0.05
        total_weight += 5
    
    # Education score (weight: 10%)
    if "education" in personal_data:
        education_result = calculate_education_score(personal_data["education"])
        factors.append({
            "factor": ScoringFactor.EDUCATION.value,
            "score": education_result["score"],
            "weight": 10,
            "weighted_score": education_result["score"] * 0.10,
            "details": education_result
        })
        total_weighted_score += education_result["score"] * 0.10
        total_weight += 10
    
    # Employment score (weight: 20%)
    if "employment_type" in personal_data:
        employment_result = calculate_employment_score(
            personal_data["employment_type"],
            personal_data.get("employment_duration_months", 0)
        )
        factors.append({
            "factor": ScoringFactor.EMPLOYMENT.value,
            "score": employment_result["score"],
            "weight": 20,
            "weighted_score": employment_result["score"] * 0.20,
            "details": employment_result
        })
        total_weighted_score += employment_result["score"] * 0.20
        total_weight += 20
    
    # Income score (weight: 20%)
    if "monthly_income" in personal_data and "income_source" in personal_data:
        income_result = calculate_income_score(
            personal_data["monthly_income"],
            personal_data["income_source"]
        )
        factors.append({
            "factor": ScoringFactor.INCOME.value,
            "score": income_result["score"],
            "weight": 20,
            "weighted_score": income_result["score"] * 0.20,
            "details": income_result
        })
        total_weighted_score += income_result["score"] * 0.20
        total_weight += 20
    
    # Living arrangement score (weight: 5%)
    if "living_arrangement" in personal_data:
        living_result = calculate_living_score(personal_data["living_arrangement"])
        factors.append({
            "factor": ScoringFactor.LIVING_ARRANGEMENT.value,
            "score": living_result["score"],
            "weight": 5,
            "weighted_score": living_result["score"] * 0.05,
            "details": living_result
        })
        total_weighted_score += living_result["score"] * 0.05
        total_weight += 5
    
    # PDN score (weight: 15%)
    pdn_result = calculate_pdn_score(pdn_risk_level)
    factors.append({
        "factor": ScoringFactor.PDN.value,
        "score": pdn_result["score"],
        "weight": 15,
        "weighted_score": pdn_result["score"] * 0.15,
        "details": pdn_result
    })
    total_weighted_score += pdn_result["score"] * 0.15
    total_weight += 15
    
    # Loan history score (weight: 10%)
    if loan_history:
        history_result = calculate_loan_history_score(
            loan_history.get("total_loans", 0),
            loan_history.get("active_loans", 0),
            loan_history.get("overdue_loans", 0)
        )
        factors.append({
            "factor": ScoringFactor.LOAN_HISTORY.value,
            "score": history_result["score"],
            "weight": 10,
            "weighted_score": history_result["score"] * 0.10,
            "details": history_result
        })
        total_weighted_score += history_result["score"] * 0.10
        total_weight += 10
    
    # Device score (weight: 3%)
    if device_info and "device_type" in device_info:
        device_result = calculate_device_score(device_info["device_type"])
        factors.append({
            "factor": ScoringFactor.DEVICE_TYPE.value,
            "score": device_result["score"],
            "weight": 3,
            "weighted_score": device_result["score"] * 0.03,
            "details": device_result
        })
        total_weighted_score += device_result["score"] * 0.03
        total_weight += 3
    
    # Region score (weight: 2%)
    if device_info and "region" in device_info:
        region_result = calculate_region_score(device_info["region"])
        factors.append({
            "factor": ScoringFactor.REGION.value,
            "score": region_result["score"],
            "weight": 2,
            "weighted_score": region_result["score"] * 0.02,
            "details": region_result
        })
        total_weighted_score += region_result["score"] * 0.02
        total_weight += 2
    
    # Referral bonus (fixed +50 points if has referral)
    if has_referral:
        factors.append({
            "factor": ScoringFactor.REFERRAL.value,
            "score": 50,
            "weight": 0,  # Fixed bonus, not weighted
            "weighted_score": 50,
            "details": {"score": 50, "reason": "Бонус за реферальную программу"}
        })
    
    # Calculate final score (normalize to 100% if not all factors present)
    if total_weight > 0:
        normalized_score = (total_weighted_score / total_weight) * 100
    else:
        normalized_score = 50  # Default score
    
    # Add referral bonus to final score
    final_score = int(normalized_score + (50 if has_referral else 0))
    
    # Scale to 300-900 range
    scaled_score = min(900, max(300, 300 + (final_score * 6)))
    
    # Determine category
    if scaled_score >= 800:
        category = ScoreCategory.EXCELLENT
        approval_probability = 95
    elif scaled_score >= 700:
        category = ScoreCategory.GOOD
        approval_probability = 80
    elif scaled_score >= 600:
        category = ScoreCategory.FAIR
        approval_probability = 60
    elif scaled_score >= 500:
        category = ScoreCategory.POOR
        approval_probability = 30
    else:
        category = ScoreCategory.VERY_POOR
        approval_probability = 10
    
    return {
        "credit_score": scaled_score,
        "category": category.value,
        "approval_probability": approval_probability,
        "factors": factors,
        "summary": {
            "total_factors": len(factors),
            "weighted_score": round(total_weighted_score, 2),
            "has_referral_bonus": has_referral,
            "calculation_date": datetime.now().isoformat()
        },
        "recommendations": get_score_recommendations(category, factors)
    }


def get_score_recommendations(category: ScoreCategory, factors: List[Dict]) -> List[str]:
    """Generate recommendations based on score category and weak factors"""
    recommendations = []
    
    # General recommendations by category
    if category == ScoreCategory.EXCELLENT:
        recommendations.append("Отличный кредитный рейтинг! Вам доступны лучшие условия.")
    elif category == ScoreCategory.GOOD:
        recommendations.append("Хороший кредитный рейтинг. Вам доступно большинство предложений.")
    elif category == ScoreCategory.FAIR:
        recommendations.append("Средний кредитный рейтинг. Рекомендуем улучшить показатели.")
    elif category == ScoreCategory.POOR:
        recommendations.append("Низкий кредитный рейтинг. Доступны ограниченные предложения.")
    else:
        recommendations.append("Очень низкий рейтинг. Рекомендуем отложить заявку.")
    
    # Specific recommendations for low-scoring factors
    for factor in factors:
        if factor["score"] < 50:
            if factor["factor"] == ScoringFactor.EMPLOYMENT.value:
                recommendations.append("Рекомендуем проработать на текущем месте минимум 6 месяцев")
            elif factor["factor"] == ScoringFactor.INCOME.value:
                recommendations.append("Рассмотрите возможность увеличения дохода или выбора меньшей суммы")
            elif factor["factor"] == ScoringFactor.PDN.value:
                recommendations.append("Снизьте долговую нагрузку перед новым займом")
            elif factor["factor"] == ScoringFactor.LOAN_HISTORY.value:
                recommendations.append("Погасите существующие займы для улучшения истории")
    
    return recommendations