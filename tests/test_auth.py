import pytest
from unittest.mock import patch, Mock


class TestAuth:
    """Test authentication endpoints"""
    
    def test_request_code_success(self, client):
        """Test successful code request"""
        with patch('app.services.telegram_gateway.TelegramGatewayService.send_code') as mock_send:
            mock_send.return_value = True
            
            response = client.post(
                "/api/v1/auth/request",
                json={"phone_number": "+998901234567"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "code_sent" in data
    
    def test_request_code_invalid_phone(self, client):
        """Test code request with invalid phone"""
        response = client.post(
            "/api/v1/auth/request",
            json={"phone_number": "123"}
        )
        
        assert response.status_code == 422
    
    def test_verify_code_success(self, client, test_user):
        """Test successful code verification"""
        with patch('app.core.redis.get_redis_client') as mock_redis_func:
            mock_redis = Mock()
            mock_redis.get.return_value = b"123456"
            mock_redis_func.return_value = mock_redis
            
            response = client.post(
                "/api/v1/auth/verify",
                json={
                    "phone_number": test_user.phone_number,
                    "code": "123456"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "token_type" in data
            assert data["token_type"] == "bearer"
            assert "user" in data
            assert data["user"]["phone_number"] == test_user.phone_number
    
    def test_verify_code_invalid(self, client, test_user):
        """Test verification with invalid code"""
        with patch('app.core.redis.get_redis_client') as mock_redis_func:
            mock_redis = Mock()
            mock_redis.get.return_value = b"123456"
            mock_redis_func.return_value = mock_redis
            
            response = client.post(
                "/api/v1/auth/verify",
                json={
                    "phone_number": test_user.phone_number,
                    "code": "999999"
                }
            )
            
            assert response.status_code == 400
            assert "Invalid verification code" in response.json()["detail"]
    
    def test_verify_code_expired(self, client, test_user):
        """Test verification with expired code"""
        with patch('app.core.redis.get_redis_client') as mock_redis_func:
            mock_redis = Mock()
            mock_redis.get.return_value = None  # Code not found
            mock_redis_func.return_value = mock_redis
            
            response = client.post(
                "/api/v1/auth/verify",
                json={
                    "phone_number": test_user.phone_number,
                    "code": "123456"
                }
            )
            
            assert response.status_code == 400
            assert "expired" in response.json()["detail"].lower()
    
    def test_check_phone_exists(self, client, test_user):
        """Test checking if phone exists"""
        response = client.get(
            f"/api/v1/auth/check-phone?phone={test_user.phone_number}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert data["is_active"] is True
    
    def test_check_phone_not_exists(self, client):
        """Test checking if phone doesn't exist"""
        response = client.get(
            "/api/v1/auth/check-phone?phone=%2B998901234599"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
        assert data["is_active"] is False
    
    def test_get_me_authenticated(self, client, auth_headers):
        """Test getting current user info"""
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "phone_number" in data
        assert "referral_code" in data
    
    def test_get_me_unauthenticated(self, client):
        """Test getting current user without auth"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
    
    def test_logout(self, client, auth_headers):
        """Test logout"""
        response = client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_rate_limiting(self, client):
        """Test rate limiting on code requests"""
        with patch('app.core.redis.get_redis_client') as mock_redis_func:
            mock_redis = Mock()
            # Simulate rate limit exceeded
            mock_redis.get.side_effect = [b"5", None]  # 5 attempts already
            mock_redis.incr.return_value = 6
            mock_redis.expire.return_value = True
            mock_redis_func.return_value = mock_redis
            
            response = client.post(
                "/api/v1/auth/request",
                json={"phone_number": "+998901234567"}
            )
            
            assert response.status_code == 429
            assert "Too many requests" in response.json()["detail"]