import pytest


class TestPersonalData:
    """Test personal data endpoints"""
    
    def test_create_personal_data(self, client, auth_headers):
        """Test creating personal data"""
        personal_data = {
            "first_name": "John",
            "last_name": "Doe",
            "middle_name": "Smith",
            "passport_series": "AB",
            "passport_number": "1234567",
            "passport_issue_date": "2020-01-01",
            "passport_issued_by": "Test Authority",
            "pin": "12345678901234",
            "birth_date": "1990-01-01",
            "birth_place": "Tashkent",
            "residence_address": "123 Test St",
            "phone_number": "+998901234567",
            "additional_phone": "+998901234568",
            "work_place": "Test Company",
            "work_position": "Manager",
            "work_experience_months": 36,
            "monthly_income": 7000000,
            "monthly_expenses": 2000000,
            "marital_status": "single",
            "children_count": 0,
            "contact_person_name": "Jane Doe",
            "contact_person_phone": "+998901234569",
            "contact_person_relation": "spouse"
        }
        
        response = client.post(
            "/api/v1/personal-data",
            headers=auth_headers,
            json=personal_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == personal_data["first_name"]
        assert data["last_name"] == personal_data["last_name"]
        assert "id" in data
    
    def test_get_personal_data(self, client, auth_headers, test_personal_data):
        """Test getting personal data"""
        response = client.get(
            "/api/v1/personal-data",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == test_personal_data.first_name
        assert data["last_name"] == test_personal_data.last_name
    
    def test_update_personal_data(self, client, auth_headers, test_personal_data):
        """Test updating personal data"""
        update_data = {
            "monthly_income": 8000000,
            "work_position": "Senior Manager"
        }
        
        response = client.patch(
            "/api/v1/personal-data",
            headers=auth_headers,
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["monthly_income"] == update_data["monthly_income"]
        assert data["work_position"] == update_data["work_position"]
    
    def test_validate_personal_data(self, client, auth_headers):
        """Test validating personal data without saving"""
        invalid_data = {
            "first_name": "A",  # Too short
            "last_name": "",    # Empty
            "passport_series": "ABC",  # Too long
            "passport_number": "123",  # Too short
            "birth_date": "2025-01-01",  # Future date
            "monthly_income": -1000  # Negative
        }
        
        response = client.post(
            "/api/v1/personal-data/validate",
            headers=auth_headers,
            json=invalid_data
        )
        
        assert response.status_code == 400
        errors = response.json()["detail"]
        assert isinstance(errors, list)
        assert len(errors) > 0
    
    def test_check_completeness(self, client, auth_headers, test_personal_data):
        """Test checking data completeness"""
        response = client.get(
            "/api/v1/personal-data/completeness",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "is_complete" in data
        assert "missing_fields" in data
        assert "completion_percentage" in data
        assert data["is_complete"] is True
        assert data["completion_percentage"] == 100
    
    def test_export_personal_data(self, client, auth_headers, test_personal_data):
        """Test exporting personal data (GDPR)"""
        response = client.get(
            "/api/v1/personal-data/export",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "personal_data" in data
        assert "created_at" in data
        assert data["personal_data"]["first_name"] == test_personal_data.first_name
    
    def test_get_summary(self, client, auth_headers, test_personal_data):
        """Test getting personal data summary"""
        response = client.get(
            "/api/v1/personal-data/summary",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "full_name" in data
        assert "age" in data
        assert "work_info" in data
        assert "financial_info" in data
    
    def test_personal_data_validation_rules(self, client, auth_headers):
        """Test specific validation rules"""
        # Test passport validation
        response = client.post(
            "/api/v1/personal-data/validate",
            headers=auth_headers,
            json={
                "passport_series": "12",  # Should be letters
                "passport_number": "ABC"  # Should be numbers
            }
        )
        
        assert response.status_code == 400
        
        # Test phone validation
        response = client.post(
            "/api/v1/personal-data/validate",
            headers=auth_headers,
            json={
                "phone_number": "123456"  # Invalid format
            }
        )
        
        assert response.status_code == 400
        
        # Test PIN validation
        response = client.post(
            "/api/v1/personal-data/validate",
            headers=auth_headers,
            json={
                "pin": "123"  # Too short
            }
        )
        
        assert response.status_code == 400