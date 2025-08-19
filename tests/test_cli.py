"""
Unit tests for the CLI functionality.
"""

from io import StringIO
from unittest.mock import patch

from contrib_checker.cli import create_parser, main


class TestCLI:
    """Test CLI functionality."""
    
    def test_create_parser(self):
        """Test argument parser creation."""
        parser = create_parser()
        
        # Test default values
        args = parser.parse_args([])
        assert args.mode == 'warn'
        assert str(args.repo_path) == '.'
        assert args.ignore_emails is None
        assert args.ignore_logins is None
        assert args.from_sha is None
        assert args.to_sha is None
        assert args.verbose is False
    
    def test_parser_with_arguments(self):
        """Test parser with various arguments."""
        parser = create_parser()
        
        args = parser.parse_args([
            '--repo-path', '/tmp/test',
            '--mode', 'fail',
            '--ignore-emails', 'bot1@example.com',
            '--ignore-emails', 'bot2@example.com',
            '--ignore-logins', 'bot1',
            '--ignore-logins', 'bot2',
            '--from-sha', 'abc123',
            '--to-sha', 'def456',
            '--verbose'
        ])
        
        assert str(args.repo_path) == '/tmp/test'
        assert args.mode == 'fail'
        assert args.ignore_emails == ['bot1@example.com', 'bot2@example.com']
        assert args.ignore_logins == ['bot1', 'bot2']
        assert args.from_sha == 'abc123'
        assert args.to_sha == 'def456'
        assert args.verbose is True
    
    def test_help_output(self):
        """Test help output."""
        parser = create_parser()
        
        with patch('sys.stderr', new_callable=StringIO):
            try:
                parser.parse_args(['--help'])
            except SystemExit as e:
                assert e.code == 0
                
        # Help should be printed to stderr (by argparse)
        # We can't easily capture it, but we can test that --help doesn't crash
    
    def test_main_help(self):
        """Test main function with help."""
        with patch('sys.exit') as mock_exit:
            main(['--help'])
            mock_exit.assert_called_once_with(0)
    
    def test_main_basic_usage(self, temp_repo):
        """Test main function basic usage."""
        # Create a simple CITATION.cff file
        citation_file = temp_repo / "CITATION.cff"
        citation_file.write_text("""
cff-version: 1.2.0
title: "Test Project"
authors:
  - family-names: "Doe"
    given-names: "John"
""")
        
        with patch('contrib_checker.core.ContributorChecker.check_all_contributors') as mock_check:
            mock_check.return_value = (True, {'missing_overall': []})
            
            result = main([
                '--repo-path', str(temp_repo),
                '--mode', 'warn'
            ])
            
            assert result == 0
            mock_check.assert_called_once()
    
    def test_main_fail_mode_with_missing_contributors(self, temp_repo):
        """Test main function in fail mode with missing contributors."""
        with patch('contrib_checker.core.ContributorChecker.check_all_contributors') as mock_check:
            mock_check.return_value = (False, {'missing_overall': ['Missing Person']})
            
            result = main([
                '--repo-path', str(temp_repo),
                '--mode', 'fail'
            ])
            
            assert result == 1
    
    def test_main_warn_mode_with_missing_contributors(self, temp_repo):
        """Test main function in warn mode with missing contributors."""
        with patch('contrib_checker.core.ContributorChecker.check_all_contributors') as mock_check:
            mock_check.return_value = (False, {'missing_overall': ['Missing Person']})
            
            result = main([
                '--repo-path', str(temp_repo),
                '--mode', 'warn'
            ])
            
            # Warn mode should return 0 even with missing contributors
            assert result == 0
    
    def test_main_range_checking(self, temp_repo):
        """Test main function with range checking."""
        with patch('contrib_checker.core.ContributorChecker.check_range_contributors') as mock_check:
            mock_check.return_value = (True, {'missing_overall': []})
            
            result = main([
                '--repo-path', str(temp_repo),
                '--from-sha', 'abc123',
                '--to-sha', 'def456',
                '--verbose'
            ])
            
            assert result == 0
            mock_check.assert_called_once_with('abc123', 'def456', 'specified range')
    
    def test_main_range_checking_incomplete_args(self, temp_repo):
        """Test main function with incomplete range arguments."""
        # Only from-sha provided
        result = main([
            '--repo-path', str(temp_repo),
            '--from-sha', 'abc123'
        ])
        
        assert result == 1
        
        # Only to-sha provided
        result = main([
            '--repo-path', str(temp_repo),
            '--to-sha', 'def456'
        ])
        
        assert result == 1
    
    def test_main_with_ignore_options(self, temp_repo):
        """Test main function with ignore options."""
        with patch('contrib_checker.core.ContributorChecker.check_all_contributors') as mock_check:
            mock_check.return_value = (True, {'missing_overall': []})
            
            with patch('contrib_checker.core.ContributorChecker.__init__') as mock_init:
                mock_init.return_value = None
                
                main([
                    '--repo-path', str(temp_repo),
                    '--ignore-emails', 'bot1@example.com',
                    '--ignore-emails', 'bot2@example.com',
                    '--ignore-logins', 'bot1',
                    '--ignore-logins', 'bot2'
                ])
                
                # Check that ContributorChecker was initialized with correct config
                mock_init.assert_called_once()
                args, kwargs = mock_init.call_args
                config = kwargs['config']
                assert config['ignore_emails'] == ['bot1@example.com', 'bot2@example.com']
                assert config['ignore_logins'] == ['bot1', 'bot2']
    
    def test_main_exception_handling(self, temp_repo):
        """Test main function exception handling."""
        with patch('contrib_checker.core.ContributorChecker.check_all_contributors') as mock_check:
            mock_check.side_effect = Exception('Test error')
            
            result = main([
                '--repo-path', str(temp_repo)
            ])
            
            assert result == 1
    
    def test_main_exception_handling_verbose(self, temp_repo):
        """Test main function exception handling with verbose output."""
        with patch('contrib_checker.core.ContributorChecker.check_all_contributors') as mock_check:
            mock_check.side_effect = Exception('Test error')
            
            with patch('traceback.print_exc') as mock_traceback:
                result = main([
                    '--repo-path', str(temp_repo),
                    '--verbose'
                ])
                
                assert result == 1
                mock_traceback.assert_called_once()
    
    def test_main_as_module(self):
        """Test that main can be called without arguments (uses sys.argv)."""
        with patch('sys.argv', ['contrib-checker', '--help']):
            with patch('sys.exit') as mock_exit:
                main()
                mock_exit.assert_called_once_with(0)
