import pytest
from datetime import datetime


class TestApplications:
    """Test application endpoints"""
    
    def test_calculate_loan(self, client):
        """Test loan calculation"""
        response = client.post(
            "/api/v1/applications/calculate",
            json={
                "amount": 5000000,
                "term": 12,
                "rate": 20
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "monthly_payment" in data
        assert "total_payment" in data
        assert "overpayment" in data
        assert data["monthly_payment"] > 0
        assert data["total_payment"] > data["amount"]
    
    def test_calculate_pdn(self, client):
        """Test PDN calculation"""
        response = client.post(
            "/api/v1/applications/calculate-pdn",
            json={
                "monthly_income": 5000000,
                "monthly_expenses": 1000000,
                "loan_amount": 5000000,
                "loan_term": 12,
                "annual_rate": 20,
                "existing_payments": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "pdn_value" in data
        assert "risk_level" in data
        assert "max_loan_amount" in data
        assert data["pdn_value"] > 0
        assert data["risk_level"] in ["low", "medium", "high", "critical"]
    
    def test_pre_check(self, client):
        """Test pre-check without auth"""
        response = client.post(
            "/api/v1/applications/pre-check",
            json={
                "amount": 5000000,
                "term": 12,
                "monthly_income": 5000000,
                "monthly_expenses": 1000000,
                "existing_payments": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "scoring" in data
        assert "pdn" in data
        assert "recommendations" in data
        assert data["scoring"]["score"] > 0
    
    def test_create_application(self, client, auth_headers):
        """Test creating application"""
        response = client.post(
            "/api/v1/applications",
            headers=auth_headers,
            json={
                "amount": 5000000,
                "term": 12,
                "purpose": "personal"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["amount"] == 5000000
        assert data["term_months"] == 12
        assert data["status"] == "pending"
    
    def test_get_applications(self, client, auth_headers, test_application):
        """Test getting user applications"""
        response = client.get(
            "/api/v1/applications",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["id"] == test_application.id
    
    def test_get_application_by_id(self, client, auth_headers, test_application):
        """Test getting specific application"""
        response = client.get(
            f"/api/v1/applications/{test_application.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_application.id
        assert data["amount"] == test_application.amount
    
    def test_get_application_not_found(self, client, auth_headers):
        """Test getting non-existent application"""
        response = client.get(
            "/api/v1/applications/99999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_get_application_scoring(self, client, auth_headers, test_application, test_personal_data):
        """Test getting application scoring"""
        response = client.get(
            f"/api/v1/applications/{test_application.id}/scoring",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "category" in data
        assert "factors" in data
        assert data["score"] >= 300
        assert data["score"] <= 900
    
    def test_get_application_offers(self, client, auth_headers, test_application, test_bank_offers):
        """Test getting offers for application"""
        response = client.get(
            f"/api/v1/applications/{test_application.id}/offers",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have at least one offer based on test data
        assert len(data) > 0
        assert "bank_name" in data[0]
        assert "monthly_payment" in data[0]
    
    def test_application_validation(self, client, auth_headers):
        """Test application validation"""
        # Amount too low
        response = client.post(
            "/api/v1/applications",
            headers=auth_headers,
            json={
                "amount": 100000,  # Below minimum
                "term": 12,
                "purpose": "personal"
            }
        )
        
        assert response.status_code == 422
        
        # Term too short
        response = client.post(
            "/api/v1/applications",
            headers=auth_headers,
            json={
                "amount": 5000000,
                "term": 2,  # Below minimum
                "purpose": "personal"
            }
        )
        
        assert response.status_code == 422