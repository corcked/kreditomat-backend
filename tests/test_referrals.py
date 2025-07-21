import pytest
from app.models.user import User


class TestReferrals:
    """Test referral system endpoints"""
    
    def test_get_referral_code(self, client, auth_headers, test_user):
        """Test getting user's referral code"""
        response = client.get(
            "/api/v1/referrals/code",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "referral_code" in data
        assert "share_link" in data
        assert data["referral_code"] == test_user.referral_code
    
    def test_get_referral_stats(self, client, auth_headers, db, test_user):
        """Test getting referral statistics"""
        # Create some referrals
        for i in range(3):
            referral = User(
                phone_number=f"+99890123456{i}",
                is_active=True,
                is_verified=True,
                referred_by_id=test_user.id
            )
            db.add(referral)
        db.commit()
        
        response = client.get(
            "/api/v1/referrals/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_referrals"] == 3
        assert data["active_referrals"] == 3
        assert data["total_reward"] > 0
        assert "referrals_today" in data
        assert "conversion_rate" in data
    
    def test_get_referral_tree(self, client, auth_headers, db, test_user):
        """Test getting referral tree"""
        # Create multi-level referrals
        level1 = User(
            phone_number="+998901234580",
            is_active=True,
            referred_by_id=test_user.id
        )
        db.add(level1)
        db.commit()
        
        level2 = User(
            phone_number="+998901234581",
            is_active=True,
            referred_by_id=level1.id
        )
        db.add(level2)
        db.commit()
        
        response = client.get(
            "/api/v1/referrals/tree",
            headers=auth_headers,
            params={"depth": 2}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "referrals" in data
        assert len(data["referrals"]) == 1
        assert len(data["referrals"][0]["referrals"]) == 1
    
    def test_get_top_referrers(self, client, db):
        """Test getting top referrers (public endpoint)"""
        # Create users with different referral counts
        for i in range(3):
            user = User(
                phone_number=f"+99890123459{i}",
                is_active=True,
                referral_count=10 - i * 2
            )
            db.add(user)
        db.commit()
        
        response = client.get(
            "/api/v1/referrals/top",
            params={"limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
        # Should be sorted by referral count desc
        if len(data) > 1:
            assert data[0]["referral_count"] >= data[1]["referral_count"]
    
    def test_get_promo_materials(self, client, auth_headers):
        """Test getting promotional materials"""
        response = client.get(
            "/api/v1/referrals/promo",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "share_text" in data
        assert "share_link" in data
        assert "qr_code" in data
        assert "banners" in data
    
    def test_apply_referral_code(self, client, db):
        """Test applying referral code during registration"""
        # Create referrer
        referrer = User(
            phone_number="+998901234590",
            is_active=True,
            referral_code="REFER123"
        )
        db.add(referrer)
        db.commit()
        
        # Register new user with referral code
        with patch('app.services.telegram_gateway.TelegramGatewayService.send_code') as mock_send:
            mock_send.return_value = True
            
            # Request code with referral
            response = client.post(
                "/api/v1/auth/request",
                json={
                    "phone_number": "+998901234591",
                    "referral_code": "REFER123"
                }
            )
            
            assert response.status_code == 200
            
            # Verify and check referral was applied
            with patch('app.core.redis.get_redis_client') as mock_redis_func:
                mock_redis = Mock()
                mock_redis.get.return_value = b"123456"
                mock_redis_func.return_value = mock_redis
                
                response = client.post(
                    "/api/v1/auth/verify",
                    json={
                        "phone_number": "+998901234591",
                        "code": "123456"
                    }
                )
                
                assert response.status_code == 200
                
                # Check referral was applied
                new_user = db.query(User).filter_by(phone_number="+998901234591").first()
                assert new_user.referred_by_id == referrer.id
    
    def test_referral_limits(self, client, auth_headers, db, test_user):
        """Test referral daily limits"""
        # Set user to have reached daily limit
        test_user.referrals_today = 10
        db.commit()
        
        response = client.get(
            "/api/v1/referrals/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["can_refer_today"] is False
        assert data["referrals_today"] == 10
    
    def test_referral_rewards_calculation(self, client, auth_headers, db, test_user):
        """Test reward calculation"""
        # Create referrals with applications
        for i in range(2):
            referral = User(
                phone_number=f"+99890123459{i}",
                is_active=True,
                referred_by_id=test_user.id,
                has_active_loan=True if i == 0 else False
            )
            db.add(referral)
        db.commit()
        
        response = client.get(
            "/api/v1/referrals/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # 50k for referrer + 10k for referral with loan
        assert data["total_reward"] == 50000 * 2 + 10000 * 1