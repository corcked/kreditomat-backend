import pytest
from decimal import Decimal

from app.services.pdn import (
    calculate_pdn,
    get_pdn_risk_level,
    PDNRiskLevel,
    auto_correct_loan_params,
    calculate_max_loan_amount,
    analyze_pdn_scenario
)


class TestPDNCalculation:
    
    def test_calculate_pdn_basic(self):
        """Test basic PDN calculation"""
        pdn = calculate_pdn(
            monthly_payment=Decimal("500000"),
            monthly_income=Decimal("2000000")
        )
        assert pdn == Decimal("25.00")
    
    def test_calculate_pdn_with_other_payments(self):
        """Test PDN calculation with existing obligations"""
        pdn = calculate_pdn(
            monthly_payment=Decimal("500000"),
            monthly_income=Decimal("2000000"),
            other_monthly_payments=Decimal("300000")
        )
        assert pdn == Decimal("40.00")
    
    def test_calculate_pdn_zero_income(self):
        """Test PDN calculation with zero income"""
        with pytest.raises(ValueError, match="Monthly income must be positive"):
            calculate_pdn(
                monthly_payment=Decimal("500000"),
                monthly_income=Decimal("0")
            )
    
    def test_calculate_pdn_high_ratio(self):
        """Test PDN calculation with high ratio"""
        pdn = calculate_pdn(
            monthly_payment=Decimal("1500000"),
            monthly_income=Decimal("2000000")
        )
        assert pdn == Decimal("75.00")


class TestPDNRiskLevel:
    
    def test_risk_level_low(self):
        """Test low risk level"""
        assert get_pdn_risk_level(Decimal("20")) == PDNRiskLevel.LOW
        assert get_pdn_risk_level(Decimal("29.99")) == PDNRiskLevel.LOW
    
    def test_risk_level_medium(self):
        """Test medium risk level"""
        assert get_pdn_risk_level(Decimal("30")) == PDNRiskLevel.MEDIUM
        assert get_pdn_risk_level(Decimal("49.99")) == PDNRiskLevel.MEDIUM
    
    def test_risk_level_high(self):
        """Test high risk level"""
        assert get_pdn_risk_level(Decimal("50")) == PDNRiskLevel.HIGH
        assert get_pdn_risk_level(Decimal("64.99")) == PDNRiskLevel.HIGH
    
    def test_risk_level_critical(self):
        """Test critical risk level"""
        assert get_pdn_risk_level(Decimal("65")) == PDNRiskLevel.CRITICAL
        assert get_pdn_risk_level(Decimal("100")) == PDNRiskLevel.CRITICAL


class TestAutoCorrection:
    
    def test_no_correction_needed(self):
        """Test when no correction is needed"""
        result = auto_correct_loan_params(
            amount=Decimal("5000000"),
            annual_rate=Decimal("24"),
            months=12,
            monthly_income=Decimal("5000000")
        )
        
        assert result["corrected"] is False
        assert result["amount"] == Decimal("5000000")
        assert result["months"] == 12
        assert len(result["corrections"]) == 0
    
    def test_term_extension_correction(self):
        """Test correction by extending term"""
        result = auto_correct_loan_params(
            amount=Decimal("10000000"),
            annual_rate=Decimal("24"),
            months=12,
            monthly_income=Decimal("2000000")
        )
        
        assert result["corrected"] is True
        assert result["amount"] == Decimal("10000000")
        assert result["months"] == 36
        assert len(result["corrections"]) > 0
        assert result["corrections"][0]["type"] == "term_extended"
    
    def test_amount_reduction_correction(self):
        """Test correction by reducing amount"""
        result = auto_correct_loan_params(
            amount=Decimal("30000000"),
            annual_rate=Decimal("24"),
            months=12,
            monthly_income=Decimal("2000000"),
            target_pdn=Decimal("50")
        )
        
        assert result["corrected"] is True
        assert result["amount"] < Decimal("30000000")
        assert result["pdn"] <= Decimal("50")
        assert any(c["type"] == "amount_reduced" for c in result["corrections"])
    
    def test_correction_with_existing_obligations(self):
        """Test correction with existing monthly payments"""
        result = auto_correct_loan_params(
            amount=Decimal("10000000"),
            annual_rate=Decimal("24"),
            months=12,
            monthly_income=Decimal("3000000"),
            other_monthly_payments=Decimal("1000000")
        )
        
        assert result["corrected"] is True
        assert result["pdn"] <= Decimal("50")
    
    def test_insufficient_income(self):
        """Test when income is insufficient for any loan"""
        with pytest.raises(ValueError, match="Cannot afford any loan"):
            auto_correct_loan_params(
                amount=Decimal("5000000"),
                annual_rate=Decimal("24"),
                months=36,
                monthly_income=Decimal("1000000"),
                other_monthly_payments=Decimal("900000"),
                target_pdn=Decimal("50")
            )


class TestMaxLoanAmount:
    
    def test_calculate_max_loan_basic(self):
        """Test basic max loan calculation"""
        max_amount = calculate_max_loan_amount(
            annual_rate=Decimal("24"),
            months=12,
            monthly_income=Decimal("3000000"),
            target_pdn=Decimal("50")
        )
        
        assert max_amount > Decimal("0")
        assert max_amount <= Decimal("50000000")  # System max limit
    
    def test_calculate_max_loan_with_obligations(self):
        """Test max loan with existing obligations"""
        max_with_obligations = calculate_max_loan_amount(
            annual_rate=Decimal("24"),
            months=12,
            monthly_income=Decimal("3000000"),
            other_monthly_payments=Decimal("500000"),
            target_pdn=Decimal("50")
        )
        
        max_without_obligations = calculate_max_loan_amount(
            annual_rate=Decimal("24"),
            months=12,
            monthly_income=Decimal("3000000"),
            target_pdn=Decimal("50")
        )
        
        assert max_with_obligations < max_without_obligations
    
    def test_calculate_max_loan_zero_rate(self):
        """Test max loan with zero interest rate"""
        max_amount = calculate_max_loan_amount(
            annual_rate=Decimal("0"),
            months=12,
            monthly_income=Decimal("3000000"),
            target_pdn=Decimal("50")
        )
        
        # With 0% rate: max = monthly_payment * months
        # monthly_payment = income * 50% = 1,500,000
        # max = 1,500,000 * 12 = 18,000,000
        assert max_amount == Decimal("18000000")
    
    def test_calculate_max_loan_insufficient_income(self):
        """Test max loan with insufficient income"""
        max_amount = calculate_max_loan_amount(
            annual_rate=Decimal("24"),
            months=12,
            monthly_income=Decimal("500000"),
            other_monthly_payments=Decimal("400000"),
            target_pdn=Decimal("50")
        )
        
        assert max_amount == Decimal("1000000")  # System min limit


class TestPDNScenarioAnalysis:
    
    def test_analyze_scenario_low_risk(self):
        """Test scenario analysis for low risk"""
        analysis = analyze_pdn_scenario(
            amount=Decimal("5000000"),
            annual_rate=Decimal("24"),
            months=12,
            monthly_income=Decimal("5000000")
        )
        
        assert analysis["current_scenario"]["risk_level"] == "low"
        assert len(analysis["recommendations"]) > 0
        assert "безопасной зоне" in analysis["recommendations"][0]
    
    def test_analyze_scenario_high_risk(self):
        """Test scenario analysis for high risk"""
        analysis = analyze_pdn_scenario(
            amount=Decimal("15000000"),
            annual_rate=Decimal("24"),
            months=12,
            monthly_income=Decimal("2500000")
        )
        
        assert analysis["current_scenario"]["risk_level"] in ["high", "critical"]
        assert len(analysis["alternatives"]) > 0
        assert any("уменьшить сумму" in r.lower() for r in analysis["recommendations"])
    
    def test_analyze_scenario_with_alternatives(self):
        """Test that alternatives are provided"""
        analysis = analyze_pdn_scenario(
            amount=Decimal("10000000"),
            annual_rate=Decimal("24"),
            months=12,
            monthly_income=Decimal("3000000")
        )
        
        assert len(analysis["alternatives"]) >= 1
        
        # Check extended term alternative
        extended_term = next(
            (a for a in analysis["alternatives"] if "36 месяцев" in a["description"]),
            None
        )
        if extended_term:
            assert extended_term["months"] == 36
            assert extended_term["pdn"] < analysis["current_scenario"]["pdn"]
        
        # Check reduced amount alternative
        reduced_amount = next(
            (a for a in analysis["alternatives"] if "Уменьшить сумму" in a["description"]),
            None
        )
        if reduced_amount:
            assert reduced_amount["amount"] < Decimal("10000000")
            assert reduced_amount["pdn"] < analysis["current_scenario"]["pdn"]
    
    def test_analyze_scenario_income_analysis(self):
        """Test income analysis in scenario"""
        analysis = analyze_pdn_scenario(
            amount=Decimal("5000000"),
            annual_rate=Decimal("24"),
            months=12,
            monthly_income=Decimal("3000000"),
            other_monthly_payments=Decimal("500000")
        )
        
        income_analysis = analysis["income_analysis"]
        assert income_analysis["monthly_income"] == Decimal("3000000")
        assert income_analysis["other_payments"] == Decimal("500000")
        assert income_analysis["free_income"] == Decimal("2500000")
        assert income_analysis["free_income_percentage"] == Decimal("83.33")