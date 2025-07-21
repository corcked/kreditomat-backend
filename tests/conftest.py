import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import redis
from unittest.mock import Mock, patch

from app.main import app
from app.db.session import Base, get_db
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.models.user import User
from app.models.personal_data import PersonalData
from app.models.application import Application
from app.models.bank_offer import BankOffer

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator:
    """Create a fresh database for each test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db) -> Generator:
    """Create a test client with overridden dependencies"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    # Mock Redis
    mock_redis = Mock(spec=redis.Redis)
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.ping.return_value = True
    mock_redis.info.return_value = {
        "connected_clients": 1,
        "used_memory_human": "1M"
    }
    
    def override_get_redis():
        return mock_redis
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def settings():
    """Get test settings"""
    return get_settings()


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = Mock(spec=redis.Redis)
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.exists.return_value = False
    mock.incr.return_value = 1
    mock.expire.return_value = True
    mock.ttl.return_value = 300
    mock.ping.return_value = True
    return mock


@pytest.fixture
def test_user(db) -> User:
    """Create a test user"""
    user = User(
        phone_number="+998901234567",
        is_active=True,
        is_verified=True,
        referral_code="TEST123"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_personal_data(db, test_user) -> PersonalData:
    """Create test personal data"""
    personal_data = PersonalData(
        user_id=test_user.id,
        first_name="Test",
        last_name="User",
        passport_series="AB",
        passport_number="1234567",
        passport_issue_date="2020-01-01",
        birth_date="1990-01-01",
        birth_place="Tashkent",
        residence_address="Test Address",
        phone_number="+998901234567",
        work_place="Test Company",
        work_position="Developer",
        work_experience_months=24,
        monthly_income=5000000,
        monthly_expenses=1000000,
        contact_person_name="Contact Person",
        contact_person_phone="+998901234568",
        contact_person_relation="Friend"
    )
    db.add(personal_data)
    db.commit()
    db.refresh(personal_data)
    return personal_data


@pytest.fixture
def test_application(db, test_user) -> Application:
    """Create a test application"""
    application = Application(
        user_id=test_user.id,
        amount=5000000,
        term_months=12,
        purpose="personal",
        monthly_income=5000000,
        monthly_expenses=1000000,
        existing_loans_payment=0,
        status="pending"
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@pytest.fixture
def test_bank_offers(db) -> list[BankOffer]:
    """Create test bank offers"""
    offers = [
        BankOffer(
            name="Test Bank 1",
            logo_url="https://example.com/logo1.png",
            min_amount=1000000,
            max_amount=10000000,
            min_term_months=6,
            max_term_months=24,
            annual_rate=20.0,
            max_pdn=50.0,
            approval_time_minutes=15,
            consider_credit_history=True,
            is_active=True,
            rating=4.5,
            requirements=["Age 18+", "Income proof"],
            special_offer="First loan 0% commission"
        ),
        BankOffer(
            name="Test Bank 2",
            logo_url="https://example.com/logo2.png",
            min_amount=500000,
            max_amount=5000000,
            min_term_months=3,
            max_term_months=12,
            annual_rate=25.0,
            max_pdn=60.0,
            approval_time_minutes=30,
            consider_credit_history=False,
            is_active=True,
            rating=4.0,
            requirements=["Age 21+"],
            special_offer=None
        )
    ]
    
    for offer in offers:
        db.add(offer)
    db.commit()
    
    for offer in offers:
        db.refresh(offer)
    
    return offers


@pytest.fixture
def auth_headers(client, test_user) -> dict:
    """Get auth headers for test user"""
    # Mock the verification process
    with patch('app.services.telegram_gateway.TelegramGatewayService.send_code') as mock_send:
        mock_send.return_value = True
        
        # Request code
        response = client.post(
            "/api/v1/auth/request",
            json={"phone_number": test_user.phone_number}
        )
        assert response.status_code == 200
        
        # Mock Redis to return our test code
        with patch('app.core.redis.get_redis_client') as mock_redis_func:
            mock_redis = Mock()
            mock_redis.get.return_value = b"123456"
            mock_redis_func.return_value = mock_redis
            
            # Verify code
            response = client.post(
                "/api/v1/auth/verify",
                json={
                    "phone_number": test_user.phone_number,
                    "code": "123456"
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            return {"Authorization": f"Bearer {data['access_token']}"}