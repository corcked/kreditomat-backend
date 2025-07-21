import pytest
from decimal import Decimal
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from app.services.scoring import (
    calculate_age_score,
    calculate_gender_score,
    calculate_marital_status_score,
    calculate_education_score,
    calculate_employment_score,
    calculate_income_score,
    calculate_living_score,
    calculate_pdn_score,
    calculate_loan_history_score,
    calculate_device_score,
    calculate_region_score,
    calculate_total_score,
    ScoreCategory,
    PDNRiskLevel
)
from app.models.personal_data import (
    Gender, MaritalStatus, Education, EmploymentType,
    IncomeSource, LivingArrangement
)


class TestIndividualScores:
    
    def test_age_score(self):
        """Test age scoring"""
        # Test different age groups
        today = date.today()
        
        # 17 years old - too young
        birth_17 = today - relativedelta(years=17, months=6)
        assert calculate_age_score(birth_17)["score"] == 0
        
        # 20 years old - young adult
        birth_20 = today - relativedelta(years=20)
        assert calculate_age_score(birth_20)["score"] == 50
        
        # 30 years old - optimal age
        birth_30 = today - relativedelta(years=30)
        assert calculate_age_score(birth_30)["score"] == 100
        
        # 50 years old - mature age
        birth_50 = today - relativedelta(years=50)
        assert calculate_age_score(birth_50)["score"] == 80
        
        # 70 years old - retirement age
        birth_70 = today - relativedelta(years=70)
        assert calculate_age_score(birth_70)["score"] == 40
    
    def test_gender_score(self):
        """Test gender scoring"""
        assert calculate_gender_score(Gender.FEMALE)["score"] == 60
        assert calculate_gender_score(Gender.MALE)["score"] == 50
    
    def test_marital_status_score(self):
        """Test marital status scoring"""
        assert calculate_marital_status_score(MaritalStatus.MARRIED)["score"] == 80
        assert calculate_marital_status_score(MaritalStatus.SINGLE)["score"] == 60
        assert calculate_marital_status_score(MaritalStatus.DIVORCED)["score"] == 50
        assert calculate_marital_status_score(MaritalStatus.WIDOWED)["score"] == 55
    
    def test_education_score(self):
        """Test education scoring"""
        assert calculate_education_score(Education.HIGHER)["score"] == 90
        assert calculate_education_score(Education.INCOMPLETE_HIGHER)["score"] == 70
        assert calculate_education_score(Education.SECONDARY_SPECIAL)["score"] == 60
        assert calculate_education_score(Education.SECONDARY)["score"] == 50
        assert calculate_education_score(Education.OTHER)["score"] == 40
    
    def test_employment_score(self):
        """Test employment scoring with duration"""
        # Full-time with different durations
        result = calculate_employment_score(EmploymentType.FULL_TIME, 3)
        assert result["score"] == 80  # 100 - 20 for short duration
        
        result = calculate_employment_score(EmploymentType.FULL_TIME, 12)
        assert result["score"] == 110  # 100 + 10 for 1 year
        
        result = calculate_employment_score(EmploymentType.FULL_TIME, 48)
        assert result["score"] == 120  # 100 + 20 for 4+ years
        
        # Unemployed
        result = calculate_employment_score(EmploymentType.UNEMPLOYED, 0)
        assert result["score"] == 0  # 20 - 20
    
    def test_income_score(self):
        """Test income scoring with source"""
        # Low income salary
        result = calculate_income_score(Decimal("400000"), IncomeSource.SALARY)
        assert result["score"] == 30  # 30 * 1.0
        
        # Medium income business
        result = calculate_income_score(Decimal("1500000"), IncomeSource.BUSINESS)
        assert result["score"] == 63  # 70 * 0.9
        
        # High income salary
        result = calculate_income_score(Decimal("6000000"), IncomeSource.SALARY)
        assert result["score"] == 100  # 100 * 1.0
        
        # Pension income
        result = calculate_income_score(Decimal("800000"), IncomeSource.PENSION)
        assert result["score"] == 40  # 50 * 0.8
    
    def test_living_score(self):
        """Test living arrangement scoring"""
        assert calculate_living_score(LivingArrangement.OWN)["score"] == 80
        assert calculate_living_score(LivingArrangement.FAMILY)["score"] == 70
        assert calculate_living_score(LivingArrangement.RENT)["score"] == 50
        assert calculate_living_score(LivingArrangement.OTHER)["score"] == 40
    
    def test_pdn_score(self):
        """Test PDN risk level scoring"""
        assert calculate_pdn_score(PDNRiskLevel.LOW)["score"] == 100
        assert calculate_pdn_score(PDNRiskLevel.MEDIUM)["score"] == 70
        assert calculate_pdn_score(PDNRiskLevel.HIGH)["score"] == 40
        assert calculate_pdn_score(PDNRiskLevel.CRITICAL)["score"] == 10
    
    def test_loan_history_score(self):
        """Test loan history scoring"""
        # No loans
        result = calculate_loan_history_score(0, 0, 0)
        assert result["score"] == 60
        
        # Good history
        result = calculate_loan_history_score(2, 1, 0)
        assert result["score"] == 80
        
        # Many loans but no overdue
        result = calculate_loan_history_score(8, 3, 0)
        assert result["score"] == 40  # 50 - 10 for extra active loan
        
        # With overdue
        result = calculate_loan_history_score(3, 1, 1)
        assert result["score"] == 50  # 80 - 30 for overdue
    
    def test_device_score(self):
        """Test device type scoring"""
        assert calculate_device_score("iPhone 14")["score"] == 80
        assert calculate_device_score("iPad Pro")["score"] == 80
        assert calculate_device_score("Samsung Galaxy S23")["score"] == 60
        assert calculate_device_score("Windows Desktop")["score"] == 70
        assert calculate_device_score("Unknown Device")["score"] == 50
    
    def test_region_score(self):
        """Test region scoring"""
        assert calculate_region_score("Ташкент")["score"] == 80
        assert calculate_region_score("Tashkent City")["score"] == 80
        assert calculate_region_score("Самарканд")["score"] == 60
        assert calculate_region_score("Бухара область")["score"] == 60
        assert calculate_region_score("Каракалпакстан")["score"] == 50


class TestTotalScoreCalculation:
    
    def test_excellent_score_profile(self):
        """Test calculation for excellent profile"""
        personal_data = {
            "birth_date": date.today() - relativedelta(years=32),
            "gender": Gender.FEMALE,
            "marital_status": MaritalStatus.MARRIED,
            "education": Education.HIGHER,
            "employment_type": EmploymentType.FULL_TIME,
            "employment_duration_months": 48,
            "monthly_income": Decimal("3000000"),
            "income_source": IncomeSource.SALARY,
            "living_arrangement": LivingArrangement.OWN
        }
        
        result = calculate_total_score(
            personal_data=personal_data,
            pdn_risk_level=PDNRiskLevel.LOW,
            loan_history={"total_loans": 2, "active_loans": 0, "overdue_loans": 0},
            device_info={"device_type": "iPhone", "region": "Tashkent"},
            has_referral=True
        )
        
        assert result["category"] == ScoreCategory.EXCELLENT.value
        assert result["credit_score"] >= 800
        assert result["approval_probability"] >= 90
        assert result["summary"]["has_referral_bonus"] is True
    
    def test_poor_score_profile(self):
        """Test calculation for poor profile"""
        personal_data = {
            "birth_date": date.today() - relativedelta(years=19),
            "gender": Gender.MALE,
            "marital_status": MaritalStatus.SINGLE,
            "education": Education.SECONDARY,
            "employment_type": EmploymentType.UNEMPLOYED,
            "employment_duration_months": 0,
            "monthly_income": Decimal("300000"),
            "income_source": IncomeSource.OTHER,
            "living_arrangement": LivingArrangement.OTHER
        }
        
        result = calculate_total_score(
            personal_data=personal_data,
            pdn_risk_level=PDNRiskLevel.CRITICAL,
            loan_history={"total_loans": 5, "active_loans": 3, "overdue_loans": 2}
        )
        
        assert result["category"] in [ScoreCategory.POOR.value, ScoreCategory.VERY_POOR.value]
        assert result["credit_score"] < 600
        assert result["approval_probability"] <= 30
    
    def test_average_score_profile(self):
        """Test calculation for average profile"""
        personal_data = {
            "birth_date": date.today() - relativedelta(years=28),
            "gender": Gender.MALE,
            "marital_status": MaritalStatus.SINGLE,
            "education": Education.SECONDARY_SPECIAL,
            "employment_type": EmploymentType.CONTRACT,
            "employment_duration_months": 18,
            "monthly_income": Decimal("1200000"),
            "income_source": IncomeSource.SALARY,
            "living_arrangement": LivingArrangement.RENT
        }
        
        result = calculate_total_score(
            personal_data=personal_data,
            pdn_risk_level=PDNRiskLevel.MEDIUM
        )
        
        assert result["category"] in [ScoreCategory.FAIR.value, ScoreCategory.GOOD.value]
        assert 600 <= result["credit_score"] < 800
        assert 50 <= result["approval_probability"] <= 80
    
    def test_partial_data_scoring(self):
        """Test scoring with partial data"""
        # Minimal data
        personal_data = {
            "monthly_income": Decimal("1500000"),
            "income_source": IncomeSource.SALARY
        }
        
        result = calculate_total_score(
            personal_data=personal_data,
            pdn_risk_level=PDNRiskLevel.MEDIUM
        )
        
        assert "credit_score" in result
        assert "category" in result
        assert result["summary"]["total_factors"] >= 2  # At least income and PDN
    
    def test_referral_bonus(self):
        """Test referral bonus effect"""
        personal_data = {
            "birth_date": date.today() - relativedelta(years=25),
            "gender": Gender.MALE,
            "education": Education.HIGHER,
            "employment_type": EmploymentType.FULL_TIME,
            "employment_duration_months": 24,
            "monthly_income": Decimal("2000000"),
            "income_source": IncomeSource.SALARY
        }
        
        # Without referral
        result_no_ref = calculate_total_score(
            personal_data=personal_data,
            pdn_risk_level=PDNRiskLevel.MEDIUM,
            has_referral=False
        )
        
        # With referral
        result_with_ref = calculate_total_score(
            personal_data=personal_data,
            pdn_risk_level=PDNRiskLevel.MEDIUM,
            has_referral=True
        )
        
        # Referral should increase score
        assert result_with_ref["credit_score"] > result_no_ref["credit_score"]
        assert result_with_ref["summary"]["has_referral_bonus"] is True
        assert result_no_ref["summary"]["has_referral_bonus"] is False
    
    def test_recommendations_generation(self):
        """Test that recommendations are generated"""
        personal_data = {
            "birth_date": date.today() - relativedelta(years=22),
            "gender": Gender.MALE,
            "education": Education.SECONDARY,
            "employment_type": EmploymentType.PART_TIME,
            "employment_duration_months": 3,
            "monthly_income": Decimal("600000"),
            "income_source": IncomeSource.SALARY,
            "living_arrangement": LivingArrangement.RENT
        }
        
        result = calculate_total_score(
            personal_data=personal_data,
            pdn_risk_level=PDNRiskLevel.HIGH,
            loan_history={"total_loans": 3, "active_loans": 2, "overdue_loans": 1}
        )
        
        assert len(result["recommendations"]) > 0
        # Should have recommendations for low employment duration and high PDN
        assert any("6 месяцев" in r for r in result["recommendations"])
        assert any("долговую нагрузку" in r for r in result["recommendations"])