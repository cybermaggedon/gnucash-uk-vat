"""
Integration tests for CLI operations.

These tests verify the command-line interface works correctly
with the vat-test-service.
"""

import pytest
import subprocess
import json
import tempfile
import os
from pathlib import Path


@pytest.mark.asyncio
class TestCLIIntegration:
    """Test CLI operations end-to-end"""
    
    async def test_cli_help_command(self, vat_test_service):
        """Test that CLI help command works"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        
        result = subprocess.run(
            ['python', str(script_path), '--help'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()
        assert "gnucash-uk-vat" in result.stdout
    
    async def test_cli_init_config(self, vat_test_service, tmp_path):
        """Test CLI config initialization"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        config_file = tmp_path / "test_cli_config.json"
        
        # Test config initialization
        result = subprocess.run([
            'python', str(script_path),
            '-c', str(config_file),
            '--init-config'
        ], capture_output=True, text=True, env={**os.environ, 'HOME': str(tmp_path)})
        
        assert result.returncode == 0
        assert config_file.exists()
        
        # Verify config file was created correctly
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Check required sections exist
        assert "application" in config_data
        assert "identity" in config_data
        assert "accounts" in config_data
    
    async def test_cli_version_display(self, vat_test_service):
        """Test CLI version display"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        
        result = subprocess.run([
            'python', str(script_path),
            '--version'
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        assert "gnucash-uk-vat" in result.stdout
    
    async def test_cli_show_obligations(self, vat_test_service, integration_test_env):
        """Test CLI show obligations command"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        
        result = subprocess.run([
            'python', str(script_path),
            '-c', integration_test_env['config'],
            '-a', integration_test_env['auth'],
            '--show-obligations'
        ], capture_output=True, text=True)
        
        # Should succeed and show obligations
        assert result.returncode == 0
        assert "999150423" in result.stdout  # VRN should appear
        
        # Should show obligation periods
        output_lines = result.stdout.split('\n')
        obligation_lines = [line for line in output_lines if '#' in line and ('O' in line or 'F' in line)]
        assert len(obligation_lines) >= 1  # Should have at least one obligation
    
    async def test_cli_show_open_obligations(self, vat_test_service, integration_test_env):
        """Test CLI show open obligations command"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        
        result = subprocess.run([
            'python', str(script_path),
            '-c', integration_test_env['config'],
            '-a', integration_test_env['auth'],
            '--show-open-obligations'
        ], capture_output=True, text=True)
        
        # Should succeed and show only open obligations
        assert result.returncode == 0
        
        # Should not show fulfilled obligations (no 'F' status in output)
        output_lines = result.stdout.split('\n')
        for line in output_lines:
            if '#' in line and 'F' in line:
                # If there's an 'F', it should be part of a date, not a status
                assert 'F ' not in line  # 'F ' indicates status, not date
    
    async def test_cli_show_liabilities(self, vat_test_service, integration_test_env):
        """Test CLI show liabilities command"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        
        result = subprocess.run([
            'python', str(script_path),
            '-c', integration_test_env['config'],
            '-a', integration_test_env['auth'],
            '--show-liabilities'
        ], capture_output=True, text=True)
        
        # Should succeed and show liabilities
        assert result.returncode == 0
        
        # Should show liability amounts
        assert any(char.isdigit() for char in result.stdout)  # Should contain numbers
    
    async def test_cli_show_payments(self, vat_test_service, integration_test_env):
        """Test CLI show payments command"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        
        result = subprocess.run([
            'python', str(script_path),
            '-c', integration_test_env['config'],
            '-a', integration_test_env['auth'],
            '--show-payments'
        ], capture_output=True, text=True)
        
        # Should succeed and show payments
        assert result.returncode == 0
        
        # Should show payment amounts
        assert any(char.isdigit() for char in result.stdout)  # Should contain numbers
    
    async def test_cli_show_vat_return(self, vat_test_service, integration_test_env):
        """Test CLI show VAT return command"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        
        result = subprocess.run([
            'python', str(script_path),
            '-c', integration_test_env['config'],
            '-a', integration_test_env['auth'],
            '--show-vat-return', '#001'  # Period that exists in test data
        ], capture_output=True, text=True)
        
        # Should succeed and show VAT return
        assert result.returncode == 0
        
        # Should show VAT return fields
        assert "#001" in result.stdout
        assert any(char.isdigit() for char in result.stdout)  # Should contain numbers
    
    async def test_cli_invalid_config_file(self, vat_test_service, tmp_path):
        """Test CLI with invalid config file"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        invalid_config = tmp_path / "invalid_config.json"
        
        # Create invalid JSON file
        with open(invalid_config, 'w') as f:
            f.write("{ invalid json }")
        
        result = subprocess.run([
            'python', str(script_path),
            '-c', str(invalid_config),
            '--show-obligations'
        ], capture_output=True, text=True)
        
        # Should fail with non-zero exit code
        assert result.returncode != 0
    
    async def test_cli_missing_config_file(self, vat_test_service, tmp_path):
        """Test CLI with missing config file"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        missing_config = tmp_path / "missing_config.json"
        
        result = subprocess.run([
            'python', str(script_path),
            '-c', str(missing_config),
            '--show-obligations'
        ], capture_output=True, text=True)
        
        # Should fail with non-zero exit code
        assert result.returncode != 0
    
    async def test_cli_missing_auth_file(self, vat_test_service, integration_test_env, tmp_path):
        """Test CLI with missing auth file"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        missing_auth = tmp_path / "missing_auth.json"
        
        result = subprocess.run([
            'python', str(script_path),
            '-c', integration_test_env['config'],
            '-a', str(missing_auth),
            '--show-obligations'
        ], capture_output=True, text=True)
        
        # Should fail with non-zero exit code (no auth file)
        assert result.returncode != 0
    
    async def test_cli_authentication_url_display(self, vat_test_service, integration_test_env, tmp_path):
        """Test CLI authentication URL display"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        
        # Use a non-existent auth file to trigger authentication
        missing_auth = tmp_path / "missing_auth.json"
        
        result = subprocess.run([
            'python', str(script_path),
            '-c', integration_test_env['config'],
            '-a', str(missing_auth),
            '--show-obligations'
        ], capture_output=True, text=True)
        
        # Should show authentication URL in output or error
        output = result.stdout + result.stderr
        assert "http://localhost:8081/oauth/authorize" in output or "authenticate" in output.lower()
    
    async def test_cli_date_range_parameters(self, vat_test_service, integration_test_env):
        """Test CLI with date range parameters"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        
        result = subprocess.run([
            'python', str(script_path),
            '-c', integration_test_env['config'],
            '-a', integration_test_env['auth'],
            '--show-obligations',
            '--start', '2023-01-01',
            '--end', '2023-03-31'
        ], capture_output=True, text=True)
        
        # Should succeed with date range
        assert result.returncode == 0
        
        # Should show obligations in the specified range
        assert "999150423" in result.stdout
    
    async def test_cli_profile_parameter(self, vat_test_service, integration_test_env):
        """Test CLI with profile parameter"""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "gnucash-uk-vat"
        
        result = subprocess.run([
            'python', str(script_path),
            '-c', integration_test_env['config'],
            '-a', integration_test_env['auth'],
            '--profile', 'local',
            '--show-obligations'
        ], capture_output=True, text=True)
        
        # Should succeed with profile specified
        assert result.returncode == 0
        assert "999150423" in result.stdout