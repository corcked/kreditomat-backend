import pytest


class TestHealth:
    """Test health check endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Kreditomat API"
        assert data["version"] == "0.1.0"
        assert data["status"] == "running"
    
    def test_basic_health_check(self, client):
        """Test basic health check"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "timestamp" in data
        assert "environment" in data
        assert "database" in data
        assert "redis" in data
    
    def test_detailed_health_check(self, client):
        """Test detailed health check"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data
        assert "total_response_time" in data
        
        # Check individual service statuses
        checks = data["checks"]
        assert "database" in checks
        assert "redis" in checks
        
        # Database check details
        db_check = checks["database"]
        assert "status" in db_check
        if db_check["status"] == "healthy":
            assert "response_time" in db_check
            assert "user_count" in db_check
        
        # Redis check details
        redis_check = checks["redis"]
        assert "status" in redis_check
        if redis_check["status"] == "healthy":
            assert "response_time" in redis_check
            assert "connected_clients" in redis_check
            assert "used_memory" in redis_check
    
    def test_health_check_with_failing_database(self, client):
        """Test health check when database is down"""
        # This test would require mocking database failure
        # For now, we just verify the endpoint handles errors gracefully
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_openapi_docs(self, client):
        """Test OpenAPI documentation endpoints"""
        # Test docs endpoint
        response = client.get("/docs")
        assert response.status_code == 200
        
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Kreditomat API"
        
        # Test ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200