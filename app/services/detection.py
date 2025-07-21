import re
from typing import Dict, Any, Optional, Tuple
from ipaddress import ip_address, IPv4Address
import httpx
from user_agents import parse
from fastapi import Request

from app.core.config import get_settings
from app.core.redis import get_redis_client

settings = get_settings()
redis_client = get_redis_client()


class DeviceDetector:
    """Device and browser detection service"""
    
    @staticmethod
    def parse_user_agent(user_agent_string: str) -> Dict[str, Any]:
        """
        Parse user agent string to extract device information
        
        Args:
            user_agent_string: User-Agent header value
            
        Returns:
            Dictionary with device information
        """
        if not user_agent_string:
            return {
                "device_type": "unknown",
                "device_family": "Unknown",
                "os_family": "Unknown",
                "os_version": "Unknown",
                "browser_family": "Unknown",
                "browser_version": "Unknown",
                "is_mobile": False,
                "is_tablet": False,
                "is_pc": False,
                "is_bot": False
            }
        
        user_agent = parse(user_agent_string)
        
        # Determine device type
        if user_agent.is_mobile:
            device_type = "mobile"
        elif user_agent.is_tablet:
            device_type = "tablet"
        elif user_agent.is_pc:
            device_type = "desktop"
        elif user_agent.is_bot:
            device_type = "bot"
        else:
            device_type = "unknown"
        
        return {
            "device_type": device_type,
            "device_family": user_agent.device.family,
            "device_brand": user_agent.device.brand or "Unknown",
            "device_model": user_agent.device.model or "Unknown",
            "os_family": user_agent.os.family,
            "os_version": user_agent.os.version_string,
            "browser_family": user_agent.browser.family,
            "browser_version": user_agent.browser.version_string,
            "is_mobile": user_agent.is_mobile,
            "is_tablet": user_agent.is_tablet,
            "is_pc": user_agent.is_pc,
            "is_bot": user_agent.is_bot,
            "is_touch_capable": user_agent.is_touch_capable
        }
    
    @staticmethod
    def get_device_fingerprint(
        user_agent: str,
        accept_language: str,
        accept_encoding: str,
        ip: str
    ) -> str:
        """
        Generate device fingerprint for fraud detection
        
        Args:
            user_agent: User-Agent header
            accept_language: Accept-Language header
            accept_encoding: Accept-Encoding header
            ip: IP address
            
        Returns:
            Device fingerprint hash
        """
        import hashlib
        
        # Combine various device characteristics
        fingerprint_data = f"{user_agent}|{accept_language}|{accept_encoding}|{ip}"
        
        # Generate SHA256 hash
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()


class RegionDetector:
    """IP-based region detection service"""
    
    # Uzbekistan IP ranges (simplified example)
    UZ_IP_RANGES = [
        ("84.54.64.0", "84.54.95.255"),
        ("185.74.4.0", "185.74.7.255"),
        ("185.196.212.0", "185.196.215.255"),
        ("213.230.64.0", "213.230.127.255"),
    ]
    
    # Region mapping by IP prefix (simplified)
    REGION_BY_PREFIX = {
        "84.54.64": "Tashkent",
        "84.54.65": "Tashkent",
        "84.54.70": "Samarkand",
        "84.54.75": "Bukhara",
        "213.230.64": "Tashkent",
        "213.230.70": "Namangan",
        "213.230.80": "Andijan",
        "213.230.90": "Fergana",
    }
    
    @classmethod
    def is_uzbekistan_ip(cls, ip: str) -> bool:
        """
        Check if IP address is from Uzbekistan
        
        Args:
            ip: IP address string
            
        Returns:
            True if IP is from Uzbekistan
        """
        try:
            ip_obj = ip_address(ip)
            if not isinstance(ip_obj, IPv4Address):
                return False
            
            # Check against known UZ ranges
            for start, end in cls.UZ_IP_RANGES:
                if ip_address(start) <= ip_obj <= ip_address(end):
                    return True
            
            return False
        except:
            return False
    
    @classmethod
    def get_region_by_ip(cls, ip: str) -> Optional[str]:
        """
        Determine region by IP address
        
        Args:
            ip: IP address string
            
        Returns:
            Region name or None
        """
        try:
            # Extract first 3 octets
            parts = ip.split('.')
            if len(parts) >= 3:
                prefix = f"{parts[0]}.{parts[1]}.{parts[2]}"
                return cls.REGION_BY_PREFIX.get(prefix)
            return None
        except:
            return None
    
    @staticmethod
    async def get_location_by_ip_external(ip: str) -> Optional[Dict[str, Any]]:
        """
        Get location using external IP geolocation service
        
        Args:
            ip: IP address string
            
        Returns:
            Location data or None
        """
        # Check cache first
        cache_key = f"geo:{ip}"
        cached = await redis_client.get(cache_key)
        if cached:
            import json
            return json.loads(cached)
        
        # Skip for local/private IPs
        try:
            ip_obj = ip_address(ip)
            if ip_obj.is_private or ip_obj.is_loopback:
                return None
        except:
            return None
        
        # Use external service (example with ipapi.co)
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"https://ipapi.co/{ip}/json/",
                    headers={"User-Agent": "Kreditomat/1.0"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Cache for 24 hours
                    await redis_client.setex(
                        cache_key,
                        86400,
                        response.text
                    )
                    
                    return {
                        "ip": ip,
                        "country": data.get("country_name"),
                        "country_code": data.get("country_code"),
                        "region": data.get("region"),
                        "city": data.get("city"),
                        "latitude": data.get("latitude"),
                        "longitude": data.get("longitude"),
                        "timezone": data.get("timezone"),
                        "org": data.get("org"),
                        "asn": data.get("asn")
                    }
        except:
            pass
        
        return None


class FraudDetector:
    """Basic fraud detection based on device and location"""
    
    # Suspicious patterns
    SUSPICIOUS_USER_AGENTS = [
        "bot", "crawler", "spider", "scraper", "curl", "wget",
        "python-requests", "scrapy", "selenium"
    ]
    
    VPN_KEYWORDS = [
        "vpn", "proxy", "tor", "anonymizer", "hide", "mask"
    ]
    
    @classmethod
    def check_suspicious_user_agent(cls, user_agent: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user agent is suspicious
        
        Returns:
            (is_suspicious, reason)
        """
        if not user_agent:
            return True, "Missing user agent"
        
        ua_lower = user_agent.lower()
        
        # Check for bot patterns
        for pattern in cls.SUSPICIOUS_USER_AGENTS:
            if pattern in ua_lower:
                return True, f"Suspicious pattern: {pattern}"
        
        # Check for too short user agent
        if len(user_agent) < 20:
            return True, "User agent too short"
        
        return False, None
    
    @classmethod
    async def check_vpn_usage(cls, ip: str, org: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Check if IP belongs to VPN/proxy service
        
        Returns:
            (is_vpn, reason)
        """
        if org:
            org_lower = org.lower()
            for keyword in cls.VPN_KEYWORDS:
                if keyword in org_lower:
                    return True, f"VPN/Proxy detected: {keyword} in organization name"
        
        # Check against known VPN IP ranges (simplified)
        # In production, use a proper VPN detection service
        
        return False, None
    
    @classmethod
    async def check_device_consistency(
        cls,
        device_info: Dict[str, Any],
        declared_device: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if detected device matches declared device
        
        Returns:
            (is_consistent, reason)
        """
        if not declared_device:
            return True, None
        
        detected_type = device_info.get("device_type", "unknown")
        
        # Simple consistency check
        if declared_device.lower() == "mobile" and detected_type != "mobile":
            return False, f"Declared mobile but detected {detected_type}"
        
        if declared_device.lower() == "desktop" and detected_type not in ["desktop", "pc"]:
            return False, f"Declared desktop but detected {detected_type}"
        
        return True, None


async def analyze_request(request: Request) -> Dict[str, Any]:
    """
    Comprehensive request analysis for device and location detection
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Analysis results
    """
    # Extract headers
    user_agent = request.headers.get("user-agent", "")
    accept_language = request.headers.get("accept-language", "")
    accept_encoding = request.headers.get("accept-encoding", "")
    
    # Get client IP (considering proxy headers)
    client_ip = request.client.host
    if "x-forwarded-for" in request.headers:
        # Take first IP from X-Forwarded-For
        client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
    elif "x-real-ip" in request.headers:
        client_ip = request.headers["x-real-ip"]
    
    # Parse device info
    device_info = DeviceDetector.parse_user_agent(user_agent)
    
    # Generate device fingerprint
    fingerprint = DeviceDetector.get_device_fingerprint(
        user_agent, accept_language, accept_encoding, client_ip
    )
    
    # Check if IP is from Uzbekistan
    is_uzbekistan = RegionDetector.is_uzbekistan_ip(client_ip)
    
    # Get region from IP
    region = RegionDetector.get_region_by_ip(client_ip)
    
    # Get detailed location (if enabled)
    location_data = None
    if settings.ENABLE_IP_GEOLOCATION:
        location_data = await RegionDetector.get_location_by_ip_external(client_ip)
    
    # Fraud checks
    suspicious_ua, ua_reason = FraudDetector.check_suspicious_user_agent(user_agent)
    is_vpn, vpn_reason = await FraudDetector.check_vpn_usage(
        client_ip,
        location_data.get("org") if location_data else None
    )
    
    # Risk score (0-100, higher is riskier)
    risk_score = 0
    risk_factors = []
    
    if suspicious_ua:
        risk_score += 30
        risk_factors.append(ua_reason)
    
    if is_vpn:
        risk_score += 40
        risk_factors.append(vpn_reason)
    
    if not is_uzbekistan and settings.RESTRICT_TO_UZBEKISTAN:
        risk_score += 50
        risk_factors.append("IP not from Uzbekistan")
    
    if device_info["is_bot"]:
        risk_score += 50
        risk_factors.append("Bot detected")
    
    # Determine risk level
    if risk_score >= 70:
        risk_level = "high"
    elif risk_score >= 40:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    return {
        "device": device_info,
        "fingerprint": fingerprint,
        "ip": client_ip,
        "is_uzbekistan_ip": is_uzbekistan,
        "region": region,
        "location": location_data,
        "language": accept_language.split(",")[0] if accept_language else None,
        "risk": {
            "score": risk_score,
            "level": risk_level,
            "factors": risk_factors,
            "is_suspicious": risk_score >= 40,
            "should_block": risk_score >= 80
        },
        "timestamp": httpx._utils.format_date_time(None)
    }


async def save_device_info(user_id: str, analysis: Dict[str, Any]) -> None:
    """
    Save device information for user
    
    Args:
        user_id: User ID
        analysis: Analysis results from analyze_request
    """
    # Store in Redis for quick access
    device_key = f"device:{user_id}:{analysis['fingerprint']}"
    await redis_client.setex(
        device_key,
        86400 * 30,  # 30 days
        str(analysis)
    )
    
    # Add to user's device list
    devices_key = f"devices:{user_id}"
    await redis_client.sadd(devices_key, analysis['fingerprint'])
    
    # Store last seen device
    last_device_key = f"last_device:{user_id}"
    await redis_client.setex(
        last_device_key,
        86400 * 30,
        analysis['fingerprint']
    )


async def check_device_change(user_id: str, current_fingerprint: str) -> Dict[str, Any]:
    """
    Check if user changed device
    
    Args:
        user_id: User ID
        current_fingerprint: Current device fingerprint
        
    Returns:
        Device change information
    """
    last_device_key = f"last_device:{user_id}"
    last_fingerprint = await redis_client.get(last_device_key)
    
    if not last_fingerprint:
        return {
            "changed": False,
            "first_device": True,
            "risk_increase": 0
        }
    
    if last_fingerprint == current_fingerprint:
        return {
            "changed": False,
            "first_device": False,
            "risk_increase": 0
        }
    
    # Device changed - check how many devices user has
    devices_key = f"devices:{user_id}"
    device_count = await redis_client.scard(devices_key)
    
    # Risk increases with more devices
    risk_increase = min(20, device_count * 5)
    
    return {
        "changed": True,
        "first_device": False,
        "previous_fingerprint": last_fingerprint,
        "device_count": device_count,
        "risk_increase": risk_increase
    }