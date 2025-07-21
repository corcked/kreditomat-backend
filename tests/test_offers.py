import pytest


class TestOffers:
    """Test bank offers endpoints"""
    
    def test_get_offers(self, client, test_bank_offers):
        """Test getting all offers"""
        response = client.get("/api/v1/offers")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["name"] == test_bank_offers[0].name
    
    def test_get_offers_with_filters(self, client, test_bank_offers):
        """Test getting offers with filters"""
        # Filter by amount range
        response = client.get(
            "/api/v1/offers",
            params={
                "min_amount": 1000000,
                "max_amount": 5000000,
                "term": 12
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Both test offers should match these criteria
        assert len(data) == 2
    
    def test_get_offer_by_id(self, client, test_bank_offers):
        """Test getting specific offer"""
        offer_id = test_bank_offers[0].id
        response = client.get(f"/api/v1/offers/{offer_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == offer_id
        assert data["name"] == test_bank_offers[0].name
    
    def test_get_offer_not_found(self, client):
        """Test getting non-existent offer"""
        response = client.get("/api/v1/offers/99999")
        
        assert response.status_code == 404
    
    def test_get_featured_offers(self, client, test_bank_offers):
        """Test getting featured offers"""
        response = client.get("/api/v1/offers/featured")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should return top-rated active offers
        assert len(data) > 0
        # Should be sorted by rating desc
        if len(data) > 1:
            assert data[0]["rating"] >= data[1]["rating"]
    
    def test_compare_offers(self, client, test_bank_offers):
        """Test comparing multiple offers"""
        offer_ids = [offer.id for offer in test_bank_offers]
        
        response = client.post(
            "/api/v1/offers/compare",
            json={"offer_ids": offer_ids}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Check comparison data
        for offer in data:
            assert "id" in offer
            assert "name" in offer
            assert "annual_rate" in offer
            assert "comparison_points" in offer
    
    def test_calculate_offer(self, client, test_bank_offers):
        """Test calculating loan for specific offer"""
        offer_id = test_bank_offers[0].id
        
        response = client.post(
            f"/api/v1/offers/{offer_id}/calculate",
            json={
                "amount": 5000000,
                "term": 12
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "monthly_payment" in data
        assert "total_payment" in data
        assert "overpayment" in data
        assert "annual_rate" in data
        assert data["annual_rate"] == test_bank_offers[0].annual_rate
    
    def test_calculate_offer_invalid_params(self, client, test_bank_offers):
        """Test calculation with invalid parameters"""
        offer_id = test_bank_offers[0].id
        
        # Amount below minimum
        response = client.post(
            f"/api/v1/offers/{offer_id}/calculate",
            json={
                "amount": 100000,  # Below offer minimum
                "term": 12
            }
        )
        
        assert response.status_code == 400
        assert "amount range" in response.json()["detail"].lower()
    
    def test_get_offers_stats(self, client, test_bank_offers):
        """Test getting offers statistics"""
        response = client.get("/api/v1/offers/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_offers" in data
        assert "average_rate" in data
        assert "min_amount" in data
        assert "max_amount" in data
        assert data["total_offers"] == 2