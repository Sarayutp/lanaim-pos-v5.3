# LanAim POS v5.3 Testing Guide

## Overview
This guide provides comprehensive information about testing the LanAim POS system, including unit tests, integration tests, and production component tests.

## Test Structure

```
tests/
├── __init__.py              # Test package initialization
├── conftest.py              # Test configuration and fixtures
├── test_models.py           # Database model tests
├── test_routes.py           # Route and view tests
├── test_production.py       # Production component tests
└── test_integration.py      # End-to-end integration tests
```

## Test Categories

### 1. Unit Tests (`test_models.py`)
Tests individual components in isolation:
- **Database Models**: User, MenuItem, Order, OrderItem, DeliveryZone
- **Model Relationships**: Foreign keys, cascading deletes
- **Data Validation**: Required fields, data types, constraints
- **Business Logic**: Price calculations, status updates

### 2. Route Tests (`test_routes.py`)
Tests web application routes and views:
- **Main Routes**: Menu display, cart functionality, checkout
- **Admin Routes**: Menu management, order management, user management
- **Kitchen Routes**: Order preparation workflow
- **Delivery Routes**: Delivery management
- **API Endpoints**: JSON responses, data validation
- **Security**: Authentication, authorization, input validation

### 3. Production Component Tests (`test_production.py`)
Tests production-ready components:
- **Security Manager**: Rate limiting, input validation, password security
- **Cache Manager**: Redis caching, memory fallback, cache decorators
- **Performance Monitor**: System monitoring, health checks, metrics
- **Backup Manager**: Database backups, file compression, restoration
- **Notification Manager**: Real-time notifications, WebSocket communication

### 4. Integration Tests (`test_integration.py`)
Tests complete workflows:
- **Order Flow**: Customer ordering to delivery completion
- **Admin Workflow**: Menu and user management
- **Kitchen Workflow**: Order preparation process
- **API Integration**: External API communication
- **Real-time Features**: WebSocket notifications
- **Error Recovery**: System resilience and error handling

## Running Tests

### Quick Setup
```bash
# Install test dependencies
pip install -r requirements_test.txt

# Run all tests
./run_tests.sh all

# Run specific test categories
./run_tests.sh unit
./run_tests.sh routes
./run_tests.sh production
./run_tests.sh integration
```

### Manual Test Execution

#### Run All Tests
```bash
pytest tests/ --verbose --cov=. --cov-report=html
```

#### Run Specific Test Files
```bash
# Unit tests only
pytest tests/test_models.py -v

# Route tests only
pytest tests/test_routes.py -v

# Production tests only
pytest tests/test_production.py -v

# Integration tests only
pytest tests/test_integration.py -v
```

#### Run Specific Test Classes
```bash
# Test specific model
pytest tests/test_models.py::TestUser -v

# Test specific route category
pytest tests/test_routes.py::TestAdminRoutes -v

# Test specific production component
pytest tests/test_production.py::TestSecurityManager -v
```

#### Run Specific Test Methods
```bash
# Test specific functionality
pytest tests/test_models.py::TestUser::test_user_creation -v
pytest tests/test_routes.py::TestMainRoutes::test_menu_display -v
```

### Test Coverage

#### Generate Coverage Report
```bash
# HTML coverage report
pytest --cov=. --cov-report=html

# Terminal coverage report
pytest --cov=. --cov-report=term-missing

# XML coverage report (for CI/CD)
pytest --cov=. --cov-report=xml
```

#### Coverage Thresholds
- **Minimum Coverage**: 75%
- **Target Coverage**: 85%
- **Excellent Coverage**: 95%

### Performance Testing

#### Run Performance Tests
```bash
# Run with timing information
pytest --durations=10

# Run benchmark tests
pytest --benchmark-only

# Memory profiling
pytest --profile
```

#### Load Testing
```bash
# Install locust for load testing
pip install locust

# Run load tests (if implemented)
locust -f tests/load_tests.py
```

## Test Configuration

### Environment Variables
Set these environment variables for testing:
```bash
export FLASK_ENV=testing
export SECRET_KEY=test-secret-key
export DATABASE_URL=sqlite:///:memory:
export REDIS_URL=memory://
export WTF_CSRF_ENABLED=False
```

### Test Database
Tests use an in-memory SQLite database by default:
- **Isolation**: Each test gets a fresh database
- **Speed**: In-memory database for fast execution
- **Clean State**: No interference between tests

### Mock External Services
Tests mock external dependencies:
- **Redis**: Falls back to memory cache
- **Email**: Mock email sending
- **File Uploads**: Mock file operations
- **WebSockets**: Mock real-time notifications

## Writing New Tests

### Test File Structure
```python
"""
Test [Component Name]
Description of what this test file covers
"""

import pytest
from tests.conftest import create_test_[entity]

class Test[ComponentName]:
    """Test [component] functionality"""
    
    def test_[specific_functionality](self, app):
        """Test [specific feature]"""
        with app.app_context():
            # Test implementation
            assert condition
```

### Test Naming Conventions
- **Test Files**: `test_*.py`
- **Test Classes**: `Test*`
- **Test Methods**: `test_*`
- **Descriptive Names**: Use clear, descriptive names

### Common Test Patterns

#### Database Tests
```python
def test_model_creation(self, app):
    """Test creating a model instance"""
    with app.app_context():
        instance = create_test_model(field='value')
        
        assert instance.id is not None
        assert instance.field == 'value'
```

#### Route Tests
```python
def test_route_response(self, client):
    """Test route returns correct response"""
    response = client.get('/endpoint')
    
    assert response.status_code == 200
    assert 'expected content' in response.get_data(as_text=True)
```

#### API Tests
```python
def test_api_endpoint(self, client):
    """Test API endpoint returns JSON"""
    response = client.get('/api/endpoint')
    
    assert response.status_code == 200
    assert response.is_json
    
    data = response.get_json()
    assert 'expected_key' in data
```

#### Authentication Tests
```python
def test_protected_route(self, authenticated_client):
    """Test route requires authentication"""
    response = authenticated_client.get('/admin/endpoint')
    assert response.status_code == 200
```

### Test Fixtures

#### Using Fixtures
```python
def test_with_fixture(self, app, client, authenticated_client):
    """Test using multiple fixtures"""
    with app.app_context():
        # Use app context for database operations
        response = authenticated_client.get('/endpoint')
        assert response.status_code == 200
```

#### Creating Custom Fixtures
```python
@pytest.fixture
def sample_data(app):
    """Create sample data for tests"""
    with app.app_context():
        data = create_test_data()
        yield data
        cleanup_test_data()
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        pip install -r requirements_test.txt
    
    - name: Run tests
      run: |
        ./run_tests.sh all
    
    - name: Upload coverage
      uses: codecov/codecov-action@v1
      with:
        file: ./test-reports/coverage.xml
```

### Test Reports
After running tests, check these reports:
- **HTML Report**: `test-reports/all_tests.html`
- **Coverage Report**: `test-reports/coverage/combined/index.html`
- **Summary Report**: `test-reports/test_summary.md`

## Best Practices

### Test Organization
1. **Group Related Tests**: Use classes to group related test methods
2. **Clear Test Names**: Use descriptive names that explain what is being tested
3. **Single Responsibility**: Each test should test one specific behavior
4. **Arrange-Act-Assert**: Structure tests with clear setup, action, and verification

### Test Data
1. **Use Fixtures**: Create reusable test data with fixtures
2. **Isolation**: Ensure tests don't depend on each other
3. **Clean State**: Each test should start with a clean state
4. **Realistic Data**: Use realistic test data when possible

### Assertions
1. **Specific Assertions**: Use specific assertions rather than generic ones
2. **Multiple Assertions**: It's okay to have multiple assertions in one test
3. **Error Messages**: Include helpful error messages in assertions
4. **Edge Cases**: Test edge cases and error conditions

### Performance
1. **Fast Tests**: Keep tests fast for quick feedback
2. **Parallel Execution**: Use pytest-xdist for parallel test execution
3. **Resource Cleanup**: Clean up resources after tests
4. **Mock External Services**: Mock slow external dependencies

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Add project root to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run with python -m pytest
python -m pytest tests/
```

#### Database Issues
```bash
# Clear test database
rm -f test*.db

# Reset migrations
rm -rf migrations/
```

#### Permission Issues
```bash
# Make test runner executable
chmod +x run_tests.sh
```

#### Dependency Issues
```bash
# Reinstall test dependencies
pip install -r requirements_test.txt --force-reinstall
```

### Debug Mode
```bash
# Run tests with debugging
pytest --pdb tests/test_specific.py::test_method

# Run with print statements
pytest -s tests/test_specific.py
```

### Verbose Output
```bash
# Maximum verbosity
pytest -vvv tests/

# Show test output
pytest --capture=no tests/
```

## Test Metrics

### Key Metrics to Track
1. **Test Coverage**: Percentage of code covered by tests
2. **Test Count**: Total number of tests
3. **Test Duration**: Time taken to run tests
4. **Success Rate**: Percentage of tests passing
5. **Code Quality**: Adherence to coding standards

### Coverage Goals
- **Models**: 95%+ coverage
- **Routes**: 90%+ coverage
- **Production Components**: 85%+ coverage
- **Integration**: 80%+ coverage
- **Overall**: 85%+ coverage

## Maintenance

### Regular Tasks
1. **Update Tests**: Keep tests updated with code changes
2. **Review Coverage**: Regularly review coverage reports
3. **Performance Monitoring**: Monitor test execution time
4. **Dependency Updates**: Keep test dependencies updated
5. **Documentation**: Keep test documentation current

### Quarterly Reviews
1. **Test Strategy Review**: Evaluate test effectiveness
2. **Coverage Analysis**: Identify untested code areas
3. **Performance Optimization**: Optimize slow tests
4. **Tool Evaluation**: Evaluate new testing tools
5. **Training**: Provide testing training to team

This comprehensive testing setup ensures the LanAim POS system is thoroughly tested, reliable, and ready for production deployment.
