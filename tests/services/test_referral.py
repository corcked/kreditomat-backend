import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.referral import ReferralService
from app.models.user import User
from app.models.application import Application, ApplicationStatus


class TestReferralCodeGeneration:
    
    def test_generate_referral_code(self):
        """Test referral code generation"""
        code = ReferralService.generate_referral_code()
        
        assert len(code) == ReferralService.CODE_LENGTH
        assert code.isalnum()
        assert code.isupper() or any(c.isdigit() for c in code)
    
    def test_generate_unique_codes(self):
        """Test that generated codes are different"""
        codes = set()
        for _ in range(100):
            code = ReferralService.generate_referral_code()
            codes.add(code)
        
        # Should generate mostly unique codes
        assert len(codes) > 95  # Allow for some collisions
    
    @pytest.mark.asyncio
    async def test_create_referral_code_new(self):
        """Test creating referral code for user without one"""
        # Mock database session
        db = AsyncMock(spec=AsyncSession)
        
        # Mock user without referral code
        user = Mock(spec=User)
        user.referral_code = None
        
        db.get.return_value = user
        db.execute.return_value.scalars.return_value.first.return_value = None
        
        code = await ReferralService.create_referral_code(db, "user123")
        
        assert code is not None
        assert len(code) == ReferralService.CODE_LENGTH
        assert user.referral_code == code
        db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_referral_code_existing(self):
        """Test that existing referral code is returned"""
        db = AsyncMock(spec=AsyncSession)
        
        # Mock user with existing referral code
        user = Mock(spec=User)
        user.referral_code = "ABC123"
        
        db.get.return_value = user
        
        code = await ReferralService.create_referral_code(db, "user123")
        
        assert code == "ABC123"
        db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_referral_code_user_not_found(self):
        """Test error when user not found"""
        db = AsyncMock(spec=AsyncSession)
        db.get.return_value = None
        
        with pytest.raises(ValueError, match="User not found"):
            await ReferralService.create_referral_code(db, "user123")


class TestReferralValidation:
    
    @pytest.mark.asyncio
    async def test_validate_referral_code_valid(self):
        """Test validating valid referral code"""
        db = AsyncMock(spec=AsyncSession)
        
        # Mock user with referral code
        user = Mock(spec=User)
        user.referral_code = "ABC123"
        user.is_active = True
        
        db.execute.return_value.scalars.return_value.first.return_value = user
        
        result = await ReferralService.validate_referral_code(db, "ABC123")
        
        assert result == user
    
    @pytest.mark.asyncio
    async def test_validate_referral_code_invalid(self):
        """Test validating invalid referral code"""
        db = AsyncMock(spec=AsyncSession)
        
        # Test empty code
        result = await ReferralService.validate_referral_code(db, "")
        assert result is None
        
        # Test wrong length
        result = await ReferralService.validate_referral_code(db, "ABC")
        assert result is None
        
        # Test non-existent code
        db.execute.return_value.scalars.return_value.first.return_value = None
        result = await ReferralService.validate_referral_code(db, "XYZ789")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_referral_code_inactive_user(self):
        """Test that inactive user's code is invalid"""
        db = AsyncMock(spec=AsyncSession)
        
        # Mock inactive user
        user = Mock(spec=User)
        user.referral_code = "ABC123"
        user.is_active = False
        
        db.execute.return_value.scalars.return_value.first.return_value = None
        
        result = await ReferralService.validate_referral_code(db, "ABC123")
        assert result is None


class TestApplyReferral:
    
    @pytest.mark.asyncio
    async def test_apply_referral_success(self):
        """Test successful referral application"""
        db = AsyncMock(spec=AsyncSession)
        
        # Mock referred user
        referred_user = Mock(spec=User)
        referred_user.id = "user123"
        referred_user.referred_by_id = None
        
        # Mock referrer
        referrer = Mock(spec=User)
        referrer.id = "referrer123"
        referrer.referral_code = "ABC123"
        referrer.is_active = True
        
        db.get.return_value = referred_user
        
        # Mock validate_referral_code
        with patch.object(
            ReferralService,
            'validate_referral_code',
            return_value=referrer
        ):
            # Mock count queries
            db.execute.return_value.scalar.side_effect = [5, 20]  # Daily and total counts
            
            result = await ReferralService.apply_referral(db, "user123", "ABC123")
            
            assert result is True
            assert referred_user.referred_by_id == "referrer123"
            db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_apply_referral_already_has_referrer(self):
        """Test cannot apply referral if user already has referrer"""
        db = AsyncMock(spec=AsyncSession)
        
        # Mock user with existing referrer
        user = Mock(spec=User)
        user.referred_by_id = "existing_referrer"
        
        db.get.return_value = user
        
        result = await ReferralService.apply_referral(db, "user123", "ABC123")
        
        assert result is False
        db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_apply_referral_self_referral(self):
        """Test cannot refer yourself"""
        db = AsyncMock(spec=AsyncSession)
        
        # Mock user
        user = Mock(spec=User)
        user.id = "user123"
        user.referred_by_id = None
        
        # Mock referrer (same as user)
        referrer = Mock(spec=User)
        referrer.id = "user123"
        
        db.get.return_value = user
        
        with patch.object(
            ReferralService,
            'validate_referral_code',
            return_value=referrer
        ):
            result = await ReferralService.apply_referral(db, "user123", "ABC123")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_apply_referral_daily_limit(self):
        """Test daily referral limit"""
        db = AsyncMock(spec=AsyncSession)
        
        # Mock users
        referred_user = Mock(spec=User)
        referred_user.id = "user123"
        referred_user.referred_by_id = None
        
        referrer = Mock(spec=User)
        referrer.id = "referrer123"
        
        db.get.return_value = referred_user
        
        with patch.object(
            ReferralService,
            'validate_referral_code',
            return_value=referrer
        ):
            # Mock count - already at daily limit
            db.execute.return_value.scalar.return_value = ReferralService.MAX_REFERRALS_PER_DAY
            
            result = await ReferralService.apply_referral(db, "user123", "ABC123")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_apply_referral_total_limit(self):
        """Test total referral limit"""
        db = AsyncMock(spec=AsyncSession)
        
        # Mock users
        referred_user = Mock(spec=User)
        referred_user.id = "user123"
        referred_user.referred_by_id = None
        
        referrer = Mock(spec=User)
        referrer.id = "referrer123"
        
        db.get.return_value = referred_user
        
        with patch.object(
            ReferralService,
            'validate_referral_code',
            return_value=referrer
        ):
            # Mock counts - within daily but at total limit
            db.execute.return_value.scalar.side_effect = [
                5,  # Daily count OK
                ReferralService.MAX_TOTAL_REFERRALS  # Total limit reached
            ]
            
            result = await ReferralService.apply_referral(db, "user123", "ABC123")
            
            assert result is False


class TestReferralStats:
    
    @pytest.mark.asyncio
    async def test_get_referral_stats(self):
        """Test getting referral statistics"""
        db = AsyncMock(spec=AsyncSession)
        
        # Mock user with referrals
        user = Mock(spec=User)
        user.id = "user123"
        user.referral_code = "ABC123"
        
        # Mock referred users
        referred1 = Mock(spec=User)
        referred1.id = "ref1"
        referred1.phone_number = "+998901234567"
        referred1.created_at = datetime.now()
        referred1.is_active = True
        
        referred2 = Mock(spec=User)
        referred2.id = "ref2"
        referred2.phone_number = "+998907654321"
        referred2.created_at = datetime.now() - timedelta(days=5)
        referred2.is_active = True
        
        user.referred_users = [referred1, referred2]
        
        db.get.return_value = user
        
        # Mock completed applications count
        db.execute.return_value.scalar.side_effect = [
            1,  # referred1 has 1 completed loan
            0,  # referred2 has 0 completed loans
            3   # Daily count
        ]
        
        # Mock recent referrals query
        mock_recent = Mock()
        mock_recent.scalars.return_value = [referred1, referred2]
        db.execute.return_value = mock_recent
        
        with patch.object(ReferralService, '_get_daily_count', return_value=3):
            stats = await ReferralService.get_referral_stats(db, "user123")
        
        assert stats["referral_code"] == "ABC123"
        assert stats["total_referrals"] == 2
        assert stats["active_referrals"] == 1
        assert stats["earned_rewards"] == ReferralService.REFERRER_REWARD
        assert stats["pending_rewards"] == ReferralService.REFERRER_REWARD
        assert stats["daily_limit_remaining"] == 7  # 10 - 3
        assert stats["total_limit_remaining"] == 98  # 100 - 2
        assert len(stats["recent_referrals"]) == 2
    
    def test_generate_referral_link(self):
        """Test referral link generation"""
        link = ReferralService.generate_referral_link("ABC123")
        assert link == "https://kreditomat.uz/?ref=ABC123"


class TestReferralTree:
    
    @pytest.mark.asyncio
    async def test_get_referral_tree(self):
        """Test building referral tree"""
        db = AsyncMock(spec=AsyncSession)
        
        # Mock users
        user = Mock(spec=User)
        user.id = "user1"
        user.phone_number = "+998901234567"
        user.referral_code = "ABC123"
        
        referred1 = Mock(spec=User)
        referred1.id = "user2"
        referred1.phone_number = "+998902345678"
        referred1.created_at = datetime.now()
        referred1.referred_users = []
        
        referred2 = Mock(spec=User)
        referred2.id = "user3"
        referred2.phone_number = "+998903456789"
        referred2.created_at = datetime.now()
        
        sub_referred = Mock(spec=User)
        sub_referred.id = "user4"
        sub_referred.phone_number = "+998904567890"
        sub_referred.created_at = datetime.now()
        sub_referred.referred_users = []
        
        referred2.referred_users = [sub_referred]
        user.referred_users = [referred1, referred2]
        
        # Mock db.get calls
        db.get.side_effect = [user, referred1, referred2, sub_referred]
        
        # Mock application counts
        db.execute.return_value.scalar.side_effect = [1, 2, 0]
        
        tree = await ReferralService.get_referral_tree(db, "user1", max_depth=3)
        
        assert tree["id"] == "user1"
        assert tree["phone"] == "4567"
        assert len(tree["referrals"]) == 2
        assert tree["referrals"][1]["referrals"][0]["id"] == "user4"


class TestNetworkValue:
    
    @pytest.mark.asyncio
    async def test_calculate_network_value(self):
        """Test network value calculation"""
        db = AsyncMock(spec=AsyncSession)
        
        # Mock network collection
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([
            ("user2",), ("user3",), ("user4",)
        ]))
        db.execute.return_value = mock_result
        
        # Mock loan stats
        mock_loan_stats = Mock()
        mock_loan_stats.first.return_value = (5, 25000000)  # 5 loans, 25M sum total
        
        # Mock active users
        mock_active = Mock()
        mock_active.scalar.return_value = 2
        
        db.execute.side_effect = [
            mock_result,  # First level referrals
            Mock(__iter__=Mock(return_value=iter([]))),  # No second level
            Mock(__iter__=Mock(return_value=iter([]))),  # No third level
            mock_loan_stats,  # Loan stats
            mock_active  # Active users
        ]
        
        value = await ReferralService.calculate_network_value(db, "user1")
        
        assert value["network_size"] == 3
        assert value["total_loans"] == 5
        assert value["total_loan_volume"] == 25000000.0
        assert value["active_users_30d"] == 2
        assert value["activity_rate"] == pytest.approx(66.67, 0.01)


class TestTopReferrers:
    
    @pytest.mark.asyncio
    async def test_get_top_referrers(self):
        """Test getting top referrers"""
        db = AsyncMock(spec=AsyncSession)
        
        # Mock query result
        mock_result = [
            Mock(id="user1", phone_number="+998901234567", referral_code="ABC123", referral_count=10),
            Mock(id="user2", phone_number="+998902345678", referral_code="XYZ789", referral_count=8),
        ]
        
        db.execute.return_value = mock_result
        
        # Mock completed referrals count
        db.execute.side_effect = [
            mock_result,  # Main query
            Mock(scalar=Mock(return_value=7)),  # user1 completed
            Mock(scalar=Mock(return_value=5)),  # user2 completed
        ]
        
        top = await ReferralService.get_top_referrers(db, limit=2)
        
        assert len(top) == 2
        assert top[0]["user_id"] == "user1"
        assert top[0]["total_referrals"] == 10
        assert top[0]["completed_referrals"] == 7
        assert top[0]["total_earnings"] == 7 * ReferralService.REFERRER_REWARD