# Test Strategy for gnucash-uk-vat

This document outlines the testing strategy for the gnucash-uk-vat project. The strategy focuses on three levels of testing: unit tests, integration tests, and contract tests.

## Overview

The testing approach uses pytest as the test framework and follows a simple, maintainable structure that ensures the application works correctly without requiring access to the live HMRC service.

## Test Structure

### 1. Unit Tests

**Location:** `tests/unit/`

Unit tests verify individual components in isolation using mocks and stubs.

#### What to test:
- Configuration loading and parsing (`config.py`)
- Authentication token management (`auth.py`)
- Data model serialization/deserialization (`model.py`)
- VAT calculation logic in operations
- Fraud prevention header generation
- Error handling in individual functions

#### Example test structure:
```python
# tests/unit/test_config.py
import pytest
from gnucash_uk_vat.config import Config, initialise_config

def test_config_loading():
    # Test configuration file loading
    pass

def test_config_path_handling():
    # Test that config writes to correct file path
    pass

def test_config_get_nested_values():
    # Test nested configuration value retrieval
    pass
```

### 2. Integration Tests

**Location:** `tests/integration/`

Integration tests verify that components work together correctly using the `vat-test-service` mock server.

#### Setup:
- Start `vat-test-service` as a fixture
- Configure the application to use the test service endpoints
- Use known test data from `vat-data.json`

#### What to test:
- Full authentication flow (OAuth)
- Retrieving VAT obligations
- Submitting VAT returns
- Retrieving liabilities and payments
- Command-line operations end-to-end

#### Example test structure:
```python
# tests/integration/test_vat_submission.py
import pytest
import asyncio
import subprocess

@pytest.fixture
async def vat_test_service():
    # Start vat-test-service
    proc = subprocess.Popen([
        'python', 'scripts/vat-test-service',
        '--listen', 'localhost:8080',
        '--data', 'tests/fixtures/test-vat-data.json'
    ])
    await asyncio.sleep(1)  # Wait for service to start
    yield 'http://localhost:8080'
    proc.terminate()

@pytest.mark.asyncio
async def test_submit_vat_return_flow(vat_test_service):
    # Test complete VAT submission flow
    pass
```

### 3. Contract Tests

**Location:** `tests/contract/`

Contract tests ensure our implementation matches the HMRC API specification.

#### What to test:
- Request format validation (headers, body structure)
- Response parsing for all expected fields
- Error response handling
- API versioning compliance

#### Example test structure:
```python
# tests/contract/test_hmrc_api_contract.py
import pytest
from gnucash_uk_vat.model import Obligation, Return

def test_obligation_response_contract():
    # Verify obligation response matches HMRC spec
    pass

def test_vat_return_request_contract():
    # Verify VAT return submission format
    pass

def test_fraud_headers_contract():
    # Verify all required fraud prevention headers
    pass
```

## Test Data

### Fixtures
- `tests/fixtures/test-config.json` - Test configuration
- `tests/fixtures/test-auth.json` - Test authentication tokens
- `tests/fixtures/test-vat-data.json` - Sample VAT data for test service
- `tests/fixtures/test-gnucash.db` - Sample GnuCash database

### Test VRNs
- Use magic VRNs starting with `999` for dynamic test data
- Format: `999DDMMYY` where DD/MM/YY is the base date

## Running Tests

### All tests:
```bash
pytest
```

### Specific test levels:
```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/contract/
```

### With coverage:
```bash
pytest --cov=gnucash_uk_vat --cov-report=html
```

## CI/CD Integration

### GitHub Actions workflow:
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
          python-version: '3.8'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov pytest-mock
      - name: Run unit tests
        run: pytest tests/unit/
      - name: Run integration tests
        run: pytest tests/integration/
      - name: Run contract tests
        run: pytest tests/contract/
```

## Test Guidelines

1. **Keep tests simple** - Each test should verify one specific behavior
2. **Use descriptive names** - Test names should explain what they verify
3. **Avoid external dependencies** - All tests should run offline
4. **Mock external services** - Use vat-test-service for HMRC API calls
5. **Test edge cases** - Include tests for error conditions and edge cases
6. **Maintain test data** - Keep test fixtures up to date with API changes

## Future Considerations

- Add performance tests for large GnuCash files
- Consider property-based testing for VAT calculations
- Add mutation testing to verify test quality