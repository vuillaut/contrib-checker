"""
Integration tests for the contrib-checker package.

These tests verify that the different components work together correctly.
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import contrib_checker


class TestPackageIntegration:
    """Test package-level integration."""
    
    def test_package_version(self):
        """Test that the package has a version."""
        assert hasattr(contrib_checker, '__version__')
        assert contrib_checker.__version__ is not None
    
    def test_package_exports(self):
        """Test that the package exports the expected classes."""
        # Should be able to import main classes
        assert contrib_checker.ContributorChecker is not None
        assert contrib_checker.GitHubContributorChecker is not None
        assert contrib_checker.GitLabContributorChecker is not None
        
        # Test __all__ contains expected items
        expected_exports = [
            'ContributorChecker',
            'GitHubContributorChecker', 
            'GitLabContributorChecker'
        ]
        
        for export in expected_exports:
            assert export in contrib_checker.__all__
    
    def test_module_execution_github(self):
        """Test that GitHub module can be executed."""
        result = subprocess.run([
            sys.executable, '-m', 'contrib_checker.github'
        ], 
        capture_output=True, 
        text=True, 
        cwd=Path(__file__).parent.parent
        )
        
        # Should exit cleanly (either 0 or 1, but not crash)
        assert result.returncode in [0, 1]
        
        # Should not have import errors or syntax errors
        assert 'ImportError' not in result.stderr
        assert 'SyntaxError' not in result.stderr
        assert 'ModuleNotFoundError' not in result.stderr
    
    def test_module_execution_gitlab(self):
        """Test that GitLab module can be executed."""
        result = subprocess.run([
            sys.executable, '-m', 'contrib_checker.gitlab'
        ], 
        capture_output=True, 
        text=True, 
        cwd=Path(__file__).parent.parent
        )
        
        # Should exit cleanly (either 0 or 1, but not crash)
        assert result.returncode in [0, 1]
        
        # Should not have import errors or syntax errors
        assert 'ImportError' not in result.stderr
        assert 'SyntaxError' not in result.stderr
        assert 'ModuleNotFoundError' not in result.stderr
    
    def test_cli_execution(self):
        """Test that CLI can be executed."""
        result = subprocess.run([
            sys.executable, '-m', 'contrib_checker.cli', '--help'
        ], 
        capture_output=True, 
        text=True, 
        cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0
        assert 'usage:' in result.stdout.lower() or 'usage:' in result.stderr.lower()


class TestEndToEndWorkflow:
    """Test end-to-end workflows."""
    
    def test_github_workflow_no_pr(self, temp_repo, sample_citation_cff):
        """Test GitHub workflow when not in PR mode."""
        # Create test repository structure
        citation_file = temp_repo / "CITATION.cff"
        citation_file.write_text(sample_citation_cff)
        
        # Mock git log to return contributors that are in citation file
        with patch.dict('os.environ', {}, clear=True):
            from contrib_checker.github import GitHubContributorChecker
            
            checker = GitHubContributorChecker(repo_path=temp_repo)
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "John Doe <john@example.com>\nJane Smith <jane@example.com>\n"
                
                success = checker.check_all_contributors()
                
                # Should succeed because contributors are in citation file
                assert success is True
    
    def test_gitlab_workflow_no_mr(self, temp_repo, sample_codemeta_json):
        """Test GitLab workflow when not in MR mode."""
        # Create test repository structure
        codemeta_file = temp_repo / "codemeta.json"
        codemeta_file.write_text(sample_codemeta_json)
        
        with patch.dict('os.environ', {}, clear=True):
            from contrib_checker.gitlab import GitLabContributorChecker
            
            checker = GitLabContributorChecker(repo_path=temp_repo)
            
            with patch('subprocess.run') as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "John Doe <john@example.com>\nJane Smith <jane@example.com>\n"
                
                success = checker.check_all_contributors()
                
                # Should succeed because contributors are in codemeta file
                assert success is True
    
    def test_cli_workflow_with_both_files(self, temp_repo, sample_citation_cff, sample_codemeta_json):
        """Test CLI workflow with both CITATION.cff and codemeta.json."""
        # Create both metadata files
        citation_file = temp_repo / "CITATION.cff"
        citation_file.write_text(sample_citation_cff)
        
        codemeta_file = temp_repo / "codemeta.json"
        codemeta_file.write_text(sample_codemeta_json)
        
        from contrib_checker.cli import main
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            # Include contributors from both files
            mock_run.return_value.stdout = (
                "John Doe <john@example.com>\n"
                "Jane Smith <jane@example.com>\n"
                "Bob Wilson <bob@example.com>\n"
            )
            
            result = main([
                '--repo-path', str(temp_repo),
                '--mode', 'warn',
                '--verbose'
            ])
            
            assert result == 0
    
    def test_missing_contributors_workflow(self, temp_repo, sample_citation_cff):
        """Test workflow with missing contributors."""
        # Create citation file
        citation_file = temp_repo / "CITATION.cff"
        citation_file.write_text(sample_citation_cff)
        
        from contrib_checker.cli import main
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            # Include contributors not in citation file
            mock_run.return_value.stdout = (
                "John Doe <john@example.com>\n"  # In citation file
                "Missing Person <missing@example.com>\n"  # Not in citation file
            )
            
            # Test warn mode (should return 0)
            result = main([
                '--repo-path', str(temp_repo),
                '--mode', 'warn'
            ])
            assert result == 0
            
            # Test fail mode (should return 1)
            result = main([
                '--repo-path', str(temp_repo),
                '--mode', 'fail'
            ])
            assert result == 1
    
    def test_ignore_patterns_workflow(self, temp_repo, sample_citation_cff):
        """Test workflow with ignore patterns."""
        # Create citation file
        citation_file = temp_repo / "CITATION.cff"
        citation_file.write_text(sample_citation_cff)
        
        from contrib_checker.cli import main
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            # Include contributors that should be ignored
            mock_run.return_value.stdout = (
                "John Doe <john@example.com>\n"  # In citation file
                "dependabot[bot] <dependabot@users.noreply.github.com>\n"  # Should be ignored
                "build-bot <build@ci.example.com>\n"  # Should be ignored by our pattern
            )
            
            result = main([
                '--repo-path', str(temp_repo),
                '--mode', 'fail',
                '--ignore-emails', 'build@ci.example.com',
                '--ignore-logins', 'build-bot'
            ])
            
            # Should succeed because ignored contributors are filtered out
            assert result == 0


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_git_repository(self, temp_repo):
        """Test behavior with invalid git repository."""
        from contrib_checker.core import ContributorChecker
        
        config = {'mode': 'warn', 'ignore_emails': [], 'ignore_logins': []}
        checker = ContributorChecker(repo_path=temp_repo, config=config)
        
        # Mock git command to fail
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            
            contributors = checker.get_contributors_from_range("abc123", "def456")
            
            # Should return empty set when git fails
            assert len(contributors) == 0
    
    def test_malformed_metadata_files(self, temp_repo):
        """Test behavior with malformed metadata files."""
        from contrib_checker.core import ContributorChecker
        
        # Create malformed CITATION.cff
        citation_file = temp_repo / "CITATION.cff"
        citation_file.write_text("invalid: yaml: content: [")
        
        # Create malformed codemeta.json
        codemeta_file = temp_repo / "codemeta.json"
        codemeta_file.write_text('{"invalid": json}')
        
        config = {'mode': 'warn', 'ignore_emails': [], 'ignore_logins': []}
        checker = ContributorChecker(repo_path=temp_repo, config=config)
        
        # Should handle errors gracefully
        citation_contributors = checker.parse_citation_cff()
        codemeta_contributors = checker.parse_codemeta_json()
        
        assert len(citation_contributors) == 0
        assert len(codemeta_contributors) == 0
    
    def test_network_errors(self, temp_repo):
        """Test behavior with network errors."""
        import os
        from contrib_checker.github import GitHubContributorChecker
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_REPOSITORY': 'owner/repo',
            'PR_NUMBER': '123'
        }):
            checker = GitHubContributorChecker(repo_path=temp_repo)
            
            # Mock requests to raise an exception
            with patch('requests.post') as mock_post:
                mock_post.side_effect = Exception('Network error')
                
                result = checker.post_pr_comment(['Missing Person'])
                
                # Should handle network errors gracefully
                assert result is False
