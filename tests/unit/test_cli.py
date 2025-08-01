"""
Unit tests for CLI module.

These tests verify the CLI argument parsing and module functionality
without invoking subprocess calls.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
from io import StringIO
from pathlib import Path

from gnucash_uk_vat.cli import create_parser, now


class TestCLIParser:
    """Test command-line argument parser"""

    def test_create_parser_returns_parser(self):
        """Test that create_parser returns an ArgumentParser"""
        parser = create_parser()
        assert parser is not None
        assert hasattr(parser, 'parse_args')

    def test_parser_help_option(self):
        """Test that parser supports --help option"""
        parser = create_parser()
        
        # Capture help output
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            with pytest.raises(SystemExit) as exc_info:
                parser.parse_args(['--help'])
            assert exc_info.value.code == 0

    def test_parser_default_values(self):
        """Test parser default values"""
        parser = create_parser()
        args = parser.parse_args([])
        
        assert args.userfile == Path('user.json')
        assert args.config == Path('config.json')
        assert args.auth == 'auth.json'
        assert args.json is False
        assert args.init_config is False
        assert args.authenticate is False

    def test_parser_json_flag(self):
        """Test that --json flag is parsed correctly"""
        parser = create_parser()
        args = parser.parse_args(['--json'])
        assert args.json is True
        
        # Test short form
        args = parser.parse_args(['-j'])
        assert args.json is True

    def test_parser_config_file_option(self):
        """Test that --config option is parsed correctly"""
        parser = create_parser()
        args = parser.parse_args(['--config', 'custom-config.json'])
        assert args.config == 'custom-config.json'
        
        # Test short form
        args = parser.parse_args(['-c', 'another-config.json'])
        assert args.config == 'another-config.json'

    def test_parser_auth_file_option(self):
        """Test that --auth option is parsed correctly"""
        parser = create_parser()
        args = parser.parse_args(['--auth', 'custom-auth.json'])
        assert args.auth == 'custom-auth.json'
        
        # Test short form
        args = parser.parse_args(['-a', 'another-auth.json'])
        assert args.auth == 'another-auth.json'

    def test_parser_userfile_option(self):
        """Test that --userfile option is parsed correctly"""
        parser = create_parser()
        args = parser.parse_args(['--userfile', 'custom-user.json'])
        assert args.userfile == Path('custom-user.json')
        
        # Test short form
        args = parser.parse_args(['-u', 'another-user.json'])
        assert args.userfile == Path('another-user.json')

    def test_parser_boolean_flags(self):
        """Test various boolean flags"""
        parser = create_parser()
        
        test_flags = [
            'init_config',
            'authenticate', 
            'show_open_obligations',
            'show_obligations',
            'show_account_detail',
            'show_account_summary',
            'show_vat_return',
            'submit_vat_return',
            'show_liabilities',
            'show_payments',
            'assist'
        ]
        
        for flag in test_flags:
            flag_arg = '--' + flag.replace('_', '-')
            args = parser.parse_args([flag_arg])
            assert getattr(args, flag) is True

    def test_parser_date_options(self):
        """Test start and end date options"""
        parser = create_parser()
        args = parser.parse_args(['--start', '2023-01-01', '--end', '2023-12-31'])
        assert args.start == '2023-01-01'
        assert args.end == '2023-12-31'

    def test_parser_due_date_option(self):
        """Test due-date option"""
        parser = create_parser()
        args = parser.parse_args(['--due-date', '2023-04-30'])
        assert args.due_date == '2023-04-30'


class TestCLIUtilities:
    """Test CLI utility functions"""

    def test_now_function_returns_utc_datetime(self):
        """Test that now() function returns UTC datetime"""
        result = now()
        
        # Check it's a datetime object
        import datetime
        assert isinstance(result, datetime.datetime)
        
        # Check it has timezone info and is UTC
        assert result.tzinfo is not None
        assert result.tzinfo == datetime.timezone.utc

    def test_now_function_different_calls(self):
        """Test that sequential calls to now() return different times"""
        import time
        
        time1 = now()
        time.sleep(0.001)  # Sleep for 1ms
        time2 = now()
        
        assert time2 > time1


class TestCLIMainFunction:
    """Test CLI main function and entry points"""

    @patch('gnucash_uk_vat.cli.asyncrun')
    @patch('gnucash_uk_vat.cli.run', new_callable=Mock)
    @patch('sys.argv', ['gnucash-uk-vat', '--help'])
    def test_main_function_calls_asyncrun(self, mock_run, mock_asyncrun):
        """Test that main function calls asyncrun with run coroutine"""
        from gnucash_uk_vat.cli import main
        
        main()
        
        # Check that asyncrun was called once
        mock_asyncrun.assert_called_once()
        # Check that run was called to get the coroutine
        mock_run.assert_called_once()

    @patch('sys.stderr', new_callable=StringIO)
    @patch('gnucash_uk_vat.cli.asyncrun')
    @patch('gnucash_uk_vat.cli.run', new_callable=Mock)
    @patch('sys.argv', ['gnucash-uk-vat'])
    def test_main_function_handles_exceptions(self, mock_run, mock_asyncrun, mock_stderr):
        """Test that main function handles exceptions properly"""
        from gnucash_uk_vat.cli import main
        
        # Make asyncrun raise an exception
        mock_asyncrun.side_effect = RuntimeError("Test error")
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        assert exc_info.value.code == 1
        assert "Exception: Test error" in mock_stderr.getvalue()
