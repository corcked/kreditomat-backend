# Backend Testing Guide

## Overview

The backend uses pytest for testing with the following components:
- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test API endpoints with mocked dependencies
- **Service Tests**: Test business logic services

## Running Tests

### All Tests
```bash
pytest
```

### Specific Test File
```bash
pytest tests/test_auth.py
```

### Specific Test Class or Function
```bash
pytest tests/test_auth.py::TestAuth::test_request_code_success
```

### With Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run Only Fast Tests
```bash
pytest -m "not slow"
```

## Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── test_auth.py         # Auth endpoint tests
├── test_applications.py # Application endpoint tests
├── test_offers.py       # Offer endpoint tests
├── test_personal_data.py # Personal data tests
├── test_referrals.py    # Referral system tests
├── test_health.py       # Health check tests
├── services/            # Service unit tests
│   ├── test_detection.py
│   ├── test_pdn.py
│   ├── test_referral.py
│   └── test_scoring.py
└── unit/               # Other unit tests
```

## Writing Tests

### Basic Test Example
```python
def test_calculate_loan(client):
    response = client.post(
        "/api/v1/applications/calculate",
        json={"amount": 5000000, "term": 12, "rate": 20}
    )
    assert response.status_code == 200
    assert "monthly_payment" in response.json()
```

### Test with Authentication
```python
def test_create_application(client, auth_headers):
    response = client.post(
        "/api/v1/applications",
        headers=auth_headers,
        json={"amount": 5000000, "term": 12}
    )
    assert response.status_code == 200
```

### Test with Database
```python
def test_with_user(client, db, test_user):
    # test_user fixture creates a user in test database
    assert test_user.phone_number == "+998901234567"
```

## Fixtures

### `client`
Test client for making API requests

### `db`
Test database session

### `auth_headers`
Authorization headers for authenticated requests

### `test_user`
Creates a test user

### `test_personal_data`
Creates test personal data

### `test_application`
Creates a test application

### `test_bank_offers`
Creates test bank offers

### `mock_redis`
Mocked Redis client

## Coverage Requirements

Target coverage: 80%

Current coverage areas:
- Auth endpoints: ~90%
- Application endpoints: ~85%
- Offer endpoints: ~85%
- Personal data endpoints: ~80%
- Referral endpoints: ~80%
- Services: ~90%

## Mocking

### Mock External Services
```python
from unittest.mock import patch

@patch('app.services.telegram_gateway.TelegramGatewayService.send_code')
def test_with_mock(mock_send, client):
    mock_send.return_value = True
    # Test code
```

### Mock Redis
```python
@patch('app.core.redis.get_redis_client')
def test_with_redis(mock_redis_func, client):
    mock_redis = Mock()
    mock_redis.get.return_value = b"value"
    mock_redis_func.return_value = mock_redis
    # Test code
```

## Environment

Tests use SQLite in-memory database and mocked Redis.

Test environment variables:
```env
DATABASE_URL=sqlite:///./test.db
REDIS_URL=redis://localhost:6379
SECRET_KEY=test-secret-key
ENVIRONMENT=test
```

## CI/CD Integration

Tests run automatically in GitHub Actions on:
- Every push to main
- Every pull request

### Local CI Test
```bash
# Run tests as in CI
pytest --cov=app --cov-report=xml -v
```

## Debugging Tests

### Print Debugging
```python
def test_debug(client):
    response = client.get("/api/v1/offers")
    print(response.json())  # See output with pytest -s
```

### Interactive Debugging
```python
def test_debug(client):
    import pdb; pdb.set_trace()
    # Debugger will stop here
```

### View Test Database
```python
def test_view_db(db):
    users = db.query(User).all()
    print(f"Users in DB: {len(users)}")
```

## Common Issues

### Database Not Found
Make sure test database is created in conftest.py

### Redis Connection Error
Tests use mocked Redis, no real connection needed

### Import Errors
Ensure PYTHONPATH includes project root:
```bash
export PYTHONPATH=$PYTHONPATH:.
```

### Fixture Not Found
Check fixture is imported in conftest.py

## Best Practices

1. **Isolate Tests**: Each test should be independent
2. **Use Fixtures**: Don't repeat setup code
3. **Mock External Services**: Never call real APIs
4. **Test Edge Cases**: Empty data, invalid input, etc.
5. **Clear Names**: test_what_when_expected()
6. **Fast Tests**: Mock slow operations
7. **Cleanup**: Database is reset between tests