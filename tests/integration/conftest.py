"""
Pytest configuration for integration tests.

This module provides fixtures for running integration tests with the vat-test-service.
"""

import pytest
import pytest_asyncio
import asyncio
import subprocess
import time
import json
import tempfile
import os
import signal
from pathlib import Path


@pytest_asyncio.fixture(scope="function")
async def vat_test_service():
    """
    Start vat-test-service for integration tests.
    
    This fixture starts the mock HMRC API service and ensures it's available
    for tests. The service runs on localhost:8080 and uses test data.
    """
    # Path to test data
    test_data_path = Path(__file__).parent.parent / "fixtures" / "test-vat-data.json"
    
    # Start the vat-test-service
    proc = subprocess.Popen([
        'python', '-m', 'gnucash_uk_vat.test_service',
        '--listen', 'localhost:8081',
        '--data', str(test_data_path),
        '--secret', 'test-secret-12345'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for service to start
    await asyncio.sleep(2)
    
    # Basic verification that process started
    if proc.poll() is not None:
        raise RuntimeError("vat-test-service failed to start")
    
    yield 'http://localhost:8081'
    
    # Cleanup - terminate the service
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture
def test_config_file(tmp_path):
    """
    Create a temporary test configuration file.
    
    Returns the path to a config file that points to the test service.
    """
    config_data = {
        "accounts": {
            "kind": "piecash",
            "file": "tests/fixtures/test-gnucash.db",
            "vatDueSales": "VAT:Output:Sales",
            "vatDueAcquisitions": "VAT:Output:EU",
            "totalVatDue": "VAT:Output",
            "vatReclaimedCurrPeriod": "VAT:Input",
            "netVatDue": "VAT",
            "totalValueSalesExVAT": "Income:Sales",
            "totalValuePurchasesExVAT": "Expenses:VAT Purchases",
            "totalValueGoodsSuppliedExVAT": "Income:Sales:EU:Goods",
            "totalAcquisitionsExVAT": "Expenses:VAT Purchases:EU Reverse VAT",
            "liabilities": "VAT:Liabilities",
            "bills": "Accounts Payable"
        },
        "application": {
            "profile": "local",
            "product-name": "gnucash-uk-vat",
            "product-version": "gnucash-uk-vat-test",
            "client-id": "test-client-id",
            "client-secret": "test-client-secret",
            "terms-and-conditions-url": "http://localhost:8081/terms"
        },
        "identity": {
            "vrn": "999150423",
            "device": {
                "os-family": "Linux",
                "os-version": "Ubuntu 20.04",
                "device-manufacturer": "Test Manufacturer",
                "device-model": "Test Model",
                "id": "test-device-12345"
            },
            "user": "test-user",
            "mac-address": "00:11:22:33:44:55"
        }
    }
    
    config_file = tmp_path / "test_config.json"
    with open(config_file, 'w') as f:
        json.dump(config_data, f, indent=4)
    
    return str(config_file)


@pytest.fixture
def test_auth_file(tmp_path):
    """
    Create a temporary test authentication file.
    
    Returns the path to an auth file with test tokens.
    """
    auth_data = {
        "access_token": "test-secret-12345",  # Matches vat-test-service secret
        "refresh_token": "67890",
        "token_type": "bearer",
        "expires": "2025-12-31T23:59:59+00:00"  # Far future expiry with timezone
    }
    
    auth_file = tmp_path / "test_auth.json"
    with open(auth_file, 'w') as f:
        json.dump(auth_data, f, indent=4)
    
    return str(auth_file)


@pytest.fixture
def integration_test_env(test_config_file, test_auth_file):
    """
    Provide complete test environment for integration tests.
    
    Returns a dict with paths to config and auth files.
    """
    return {
        'config': test_config_file,
        'auth': test_auth_file
    }
