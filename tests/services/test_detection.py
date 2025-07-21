import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request

from app.services.detection import (
    DeviceDetector,
    RegionDetector,
    FraudDetector,
    analyze_request,
    save_device_info,
    check_device_change
)


class TestDeviceDetector:
    
    def test_parse_user_agent_mobile(self):
        """Test mobile device detection"""
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15"
        result = DeviceDetector.parse_user_agent(ua)
        
        assert result["device_type"] == "mobile"
        assert result["is_mobile"] is True
        assert result["is_pc"] is False
        assert "iPhone" in str(result["device_family"])
    
    def test_parse_user_agent_desktop(self):
        """Test desktop device detection"""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        result = DeviceDetector.parse_user_agent(ua)
        
        assert result["device_type"] == "desktop"
        assert result["is_pc"] is True
        assert result["is_mobile"] is False
    
    def test_parse_user_agent_bot(self):
        """Test bot detection"""
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        result = DeviceDetector.parse_user_agent(ua)
        
        assert result["device_type"] == "bot"
        assert result["is_bot"] is True
    
    def test_parse_empty_user_agent(self):
        """Test empty user agent handling"""
        result = DeviceDetector.parse_user_agent("")
        
        assert result["device_type"] == "unknown"
        assert result["device_family"] == "Unknown"
        assert result["is_mobile"] is False
    
    def test_device_fingerprint(self):
        """Test device fingerprint generation"""
        fp1 = DeviceDetector.get_device_fingerprint(
            "Mozilla/5.0", "en-US", "gzip", "192.168.1.1"
        )
        fp2 = DeviceDetector.get_device_fingerprint(
            "Mozilla/5.0", "en-US", "gzip", "192.168.1.1"
        )
        fp3 = DeviceDetector.get_device_fingerprint(
            "Mozilla/4.0", "en-US", "gzip", "192.168.1.1"
        )
        
        # Same input should produce same fingerprint
        assert fp1 == fp2
        # Different input should produce different fingerprint
        assert fp1 != fp3
        # Should be a hex string
        assert len(fp1) == 64  # SHA256 hex length


class TestRegionDetector:
    
    def test_is_uzbekistan_ip(self):
        """Test Uzbekistan IP detection"""
        # UZ IPs
        assert RegionDetector.is_uzbekistan_ip("84.54.64.1") is True
        assert RegionDetector.is_uzbekistan_ip("213.230.100.50") is True
        
        # Non-UZ IPs
        assert RegionDetector.is_uzbekistan_ip("8.8.8.8") is False
        assert RegionDetector.is_uzbekistan_ip("192.168.1.1") is False
        
        # Invalid IPs
        assert RegionDetector.is_uzbekistan_ip("invalid") is False
        assert RegionDetector.is_uzbekistan_ip("999.999.999.999") is False
    
    def test_get_region_by_ip(self):
        """Test region detection by IP"""
        assert RegionDetector.get_region_by_ip("84.54.64.100") == "Tashkent"
        assert RegionDetector.get_region_by_ip("84.54.70.50") == "Samarkand"
        assert RegionDetector.get_region_by_ip("213.230.80.100") == "Andijan"
        
        # Unknown region
        assert RegionDetector.get_region_by_ip("8.8.8.8") is None
        assert RegionDetector.get_region_by_ip("invalid") is None
    
    @pytest.mark.asyncio
    async def test_get_location_by_ip_external_private(self):
        """Test that private IPs are skipped"""
        result = await RegionDetector.get_location_by_ip_external("192.168.1.1")
        assert result is None
        
        result = await RegionDetector.get_location_by_ip_external("127.0.0.1")
        assert result is None


class TestFraudDetector:
    
    def test_check_suspicious_user_agent(self):
        """Test suspicious user agent detection"""
        # Normal user agents
        is_sus, reason = FraudDetector.check_suspicious_user_agent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        assert is_sus is False
        assert reason is None
        
        # Suspicious patterns
        is_sus, reason = FraudDetector.check_suspicious_user_agent("curl/7.64.1")
        assert is_sus is True
        assert "curl" in reason
        
        is_sus, reason = FraudDetector.check_suspicious_user_agent("python-requests/2.25.1")
        assert is_sus is True
        assert "python-requests" in reason
        
        # Missing user agent
        is_sus, reason = FraudDetector.check_suspicious_user_agent("")
        assert is_sus is True
        assert "Missing" in reason
        
        # Too short
        is_sus, reason = FraudDetector.check_suspicious_user_agent("Mozilla")
        assert is_sus is True
        assert "too short" in reason
    
    @pytest.mark.asyncio
    async def test_check_vpn_usage(self):
        """Test VPN detection"""
        # Normal ISP
        is_vpn, reason = await FraudDetector.check_vpn_usage(
            "8.8.8.8", "Google LLC"
        )
        assert is_vpn is False
        
        # VPN provider
        is_vpn, reason = await FraudDetector.check_vpn_usage(
            "1.2.3.4", "NordVPN LLC"
        )
        assert is_vpn is True
        assert "vpn" in reason.lower()
        
        # Proxy provider
        is_vpn, reason = await FraudDetector.check_vpn_usage(
            "1.2.3.4", "Anonymous Proxy Services"
        )
        assert is_vpn is True
        assert "proxy" in reason.lower()
    
    @pytest.mark.asyncio
    async def test_check_device_consistency(self):
        """Test device consistency check"""
        # Matching devices
        is_consistent, reason = await FraudDetector.check_device_consistency(
            {"device_type": "mobile"},
            "mobile"
        )
        assert is_consistent is True
        
        # Mismatched devices
        is_consistent, reason = await FraudDetector.check_device_consistency(
            {"device_type": "desktop"},
            "mobile"
        )
        assert is_consistent is False
        assert "mobile but detected desktop" in reason
        
        # No declared device
        is_consistent, reason = await FraudDetector.check_device_consistency(
            {"device_type": "mobile"},
            None
        )
        assert is_consistent is True


class TestAnalyzeRequest:
    
    @pytest.mark.asyncio
    @patch('app.services.detection.RegionDetector.get_location_by_ip_external')
    @patch('app.core.config.get_settings')
    async def test_analyze_request_normal(self, mock_settings, mock_location):
        """Test normal request analysis"""
        mock_settings.return_value.ENABLE_IP_GEOLOCATION = False
        mock_settings.return_value.RESTRICT_TO_UZBEKISTAN = True
        
        # Create mock request
        request = Mock(spec=Request)
        request.client.host = "84.54.64.100"
        request.headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "accept-language": "ru-RU,ru;q=0.9,en;q=0.8",
            "accept-encoding": "gzip, deflate"
        }
        
        result = await analyze_request(request)
        
        assert result["device"]["device_type"] == "desktop"
        assert result["ip"] == "84.54.64.100"
        assert result["is_uzbekistan_ip"] is True
        assert result["region"] == "Tashkent"
        assert result["language"] == "ru-RU"
        assert result["risk"]["level"] == "low"
        assert result["risk"]["is_suspicious"] is False
    
    @pytest.mark.asyncio
    @patch('app.services.detection.RegionDetector.get_location_by_ip_external')
    @patch('app.core.config.get_settings')
    async def test_analyze_request_suspicious(self, mock_settings, mock_location):
        """Test suspicious request analysis"""
        mock_settings.return_value.ENABLE_IP_GEOLOCATION = False
        mock_settings.return_value.RESTRICT_TO_UZBEKISTAN = True
        
        # Create mock request with bot user agent
        request = Mock(spec=Request)
        request.client.host = "8.8.8.8"  # Non-UZ IP
        request.headers = {
            "user-agent": "curl/7.64.1",
            "accept-language": "en-US",
            "accept-encoding": "gzip"
        }
        
        result = await analyze_request(request)
        
        assert result["ip"] == "8.8.8.8"
        assert result["is_uzbekistan_ip"] is False
        assert result["risk"]["level"] == "high"
        assert result["risk"]["is_suspicious"] is True
        assert len(result["risk"]["factors"]) >= 2  # curl + non-UZ
    
    @pytest.mark.asyncio
    @patch('app.services.detection.RegionDetector.get_location_by_ip_external')
    @patch('app.core.config.get_settings')
    async def test_analyze_request_with_proxy_headers(self, mock_settings, mock_location):
        """Test request with proxy headers"""
        mock_settings.return_value.ENABLE_IP_GEOLOCATION = False
        mock_settings.return_value.RESTRICT_TO_UZBEKISTAN = True
        
        request = Mock(spec=Request)
        request.client.host = "10.0.0.1"  # Proxy IP
        request.headers = {
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)",
            "x-forwarded-for": "84.54.64.200, 10.0.0.1",
            "accept-language": "uz-UZ",
            "accept-encoding": "gzip"
        }
        
        result = await analyze_request(request)
        
        # Should use real client IP from X-Forwarded-For
        assert result["ip"] == "84.54.64.200"
        assert result["is_uzbekistan_ip"] is True


class TestDeviceTracking:
    
    @pytest.mark.asyncio
    @patch('app.core.redis.get_redis')
    async def test_save_device_info(self, mock_redis):
        """Test saving device information"""
        mock_redis_client = AsyncMock()
        mock_redis.return_value = mock_redis_client
        
        analysis = {
            "fingerprint": "abc123",
            "device": {"device_type": "mobile"},
            "ip": "84.54.64.100"
        }
        
        await save_device_info("user123", analysis)
        
        # Should save device info
        mock_redis_client.setex.assert_called()
        # Should add to device set
        mock_redis_client.sadd.assert_called_with("devices:user123", "abc123")
    
    @pytest.mark.asyncio
    @patch('app.core.redis.get_redis')
    async def test_check_device_change_first_device(self, mock_redis):
        """Test first device check"""
        mock_redis_client = AsyncMock()
        mock_redis_client.get.return_value = None
        mock_redis.return_value = mock_redis_client
        
        result = await check_device_change("user123", "fingerprint123")
        
        assert result["changed"] is False
        assert result["first_device"] is True
        assert result["risk_increase"] == 0
    
    @pytest.mark.asyncio
    @patch('app.core.redis.get_redis')
    async def test_check_device_change_same_device(self, mock_redis):
        """Test same device check"""
        mock_redis_client = AsyncMock()
        mock_redis_client.get.return_value = "fingerprint123"
        mock_redis.return_value = mock_redis_client
        
        result = await check_device_change("user123", "fingerprint123")
        
        assert result["changed"] is False
        assert result["first_device"] is False
        assert result["risk_increase"] == 0
    
    @pytest.mark.asyncio
    @patch('app.core.redis.get_redis')
    async def test_check_device_change_different_device(self, mock_redis):
        """Test device change detection"""
        mock_redis_client = AsyncMock()
        mock_redis_client.get.return_value = "old_fingerprint"
        mock_redis_client.scard.return_value = 3  # 3 devices total
        mock_redis.return_value = mock_redis_client
        
        result = await check_device_change("user123", "new_fingerprint")
        
        assert result["changed"] is True
        assert result["first_device"] is False
        assert result["previous_fingerprint"] == "old_fingerprint"
        assert result["device_count"] == 3
        assert result["risk_increase"] == 15  # 3 devices * 5