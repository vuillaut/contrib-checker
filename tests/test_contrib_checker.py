#!/usr/bin/env python3
"""
Comprehensive test suite for contrib-checker package.

Tests all modules: core, github, gitlab, and cli.
"""

import pytest
import sys
import os
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from contrib_checker import ContributorChecker, GitHubContributorChecker, GitLabContributorChecker
from contrib_checker.cli import main as cli_main


class TestContributorChecker:
    """Test the core ContributorChecker functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = {
            'mode': 'warn',
            'ignore_emails': ['bot@example.com'],
            'ignore_logins': ['test-bot']
        }
        
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test ContributorChecker initialization."""
        checker = ContributorChecker(repo_path=self.temp_dir, config=self.config)
        assert checker.repo_path == self.temp_dir
        assert checker.config == self.config
    
    def test_normalize_contributor_name(self):
        """Test contributor name normalization."""
        checker = ContributorChecker(repo_path=self.temp_dir, config=self.config)
        
        test_cases = [
            ("John Doe <john@example.com>", "john doe"),
            ("  JANE  DOE  ", "jane doe"),
            ("Bob Smith <BOB@EXAMPLE.COM>", "bob smith"),
            ("Alice-Jane Wilson", "alice-jane wilson"),
            ("测试用户 <test@example.com>", "测试用户"),
        ]
        
        for input_name, expected in test_cases:
            result = checker.normalize_contributor_name(input_name)
            assert result == expected, f"Expected '{expected}', got '{result}' for input '{input_name}'"
    
    def test_parse_citation_cff(self):
        """Test CITATION.cff parsing."""
        # Create a test CITATION.cff file
        citation_content = """
cff-version: 1.2.0
title: "Test Project"
authors:
  - family-names: "Doe"
    given-names: "John"
    email: "john@example.com"
  - family-names: "Smith"
    given-names: "Jane"
    email: "jane@example.com"
"""
        citation_file = self.temp_dir / "CITATION.cff"
        citation_file.write_text(citation_content)
        
        checker = ContributorChecker(repo_path=self.temp_dir, config=self.config)
        contributors = checker.parse_citation_cff()
        
        assert len(contributors) == 2
        assert "John Doe <john@example.com>" in contributors
        assert "Jane Smith <jane@example.com>" in contributors
    
    def test_parse_codemeta_json(self):
        """Test codemeta.json parsing."""
        # Create a test codemeta.json file
        codemeta_content = """
{
  "author": [
    {
      "givenName": "John",
      "familyName": "Doe",
      "email": "john@example.com"
    },
    {
      "givenName": "Jane", 
      "familyName": "Smith",
      "email": "jane@example.com"
    }
  ]
}
"""
        codemeta_file = self.temp_dir / "codemeta.json"
        codemeta_file.write_text(codemeta_content)
        
        checker = ContributorChecker(repo_path=self.temp_dir, config=self.config)
        contributors = checker.parse_codemeta_json()
        
        assert len(contributors) == 2
        assert "John Doe <john@example.com>" in contributors
        assert "Jane Smith <jane@example.com>" in contributors
    
    @patch('subprocess.run')
    def test_get_contributors_from_range(self, mock_run):
        """Test getting contributors from git range."""
        # Mock git log output
        mock_run.return_value = Mock(
            returncode=0,
            stdout="John Doe <john@example.com>\nJane Smith <jane@example.com>\n"
        )
        
        checker = ContributorChecker(repo_path=self.temp_dir, config=self.config)
        contributors = checker.get_contributors_from_range("abc123", "def456")
        
        assert len(contributors) == 2
        assert "John Doe <john@example.com>" in contributors
        assert "Jane Smith <jane@example.com>" in contributors
        
        # Verify git command was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "git" in args
        assert "log" in args
        assert "--use-mailmap" in args
        assert "abc123..def456" in args


class TestGitHubContributorChecker:
    """Test GitHub-specific functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Mock GitHub environment variables
        self.env_patcher = patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_REPOSITORY': 'test/repo',
            'PR_NUMBER': '123',
            'PR_BASE_SHA': 'abc123',
            'PR_HEAD_SHA': 'def456',
            'ACTION_MODE': 'warn'
        })
        self.env_patcher.start()
        
    def teardown_method(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test GitHubContributorChecker initialization."""
        checker = GitHubContributorChecker(repo_path=self.temp_dir)
        
        assert checker.github_token == 'test-token'
        assert checker.github_repo == 'test/repo'
        assert checker.pr_number == '123'
        assert checker.pr_base_sha == 'abc123'
        assert checker.pr_head_sha == 'def456'
    
    def test_load_config_from_env(self):
        """Test configuration loading from environment."""
        with patch.dict(os.environ, {
            'ACTION_IGNORE_EMAILS': 'bot1@example.com,bot2@example.com',
            'ACTION_IGNORE_LOGINS': 'bot1,bot2'
        }):
            checker = GitHubContributorChecker(repo_path=self.temp_dir)
            
            assert checker.config['ignore_emails'] == ['bot1@example.com', 'bot2@example.com']
            assert checker.config['ignore_logins'] == ['bot1', 'bot2']
    
    @patch('requests.post')
    def test_post_pr_comment(self, mock_post):
        """Test posting PR comments."""
        mock_post.return_value = Mock(status_code=201)
        
        checker = GitHubContributorChecker(repo_path=self.temp_dir)
        missing_contributors = ['John Doe', 'Jane Smith']
        
        result = checker.post_pr_comment(missing_contributors)
        
        assert result is True
        mock_post.assert_called_once()
        
        # Check the API call
        call_args = mock_post.call_args
        assert 'https://api.github.com/repos/test/repo/issues/123/comments' == call_args[0][0]
        assert 'Authorization' in call_args[1]['headers']


class TestGitLabContributorChecker:
    """Test GitLab-specific functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Mock GitLab environment variables
        self.env_patcher = patch.dict(os.environ, {
            'GITLAB_TOKEN': 'test-token',
            'CI_PROJECT_ID': '123',
            'CI_MERGE_REQUEST_IID': '456',
            'CI_MERGE_REQUEST_TARGET_BRANCH_SHA': 'abc123',
            'CI_COMMIT_SHA': 'def456',
            'MODE': 'warn'
        })
        self.env_patcher.start()
        
    def teardown_method(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test GitLabContributorChecker initialization."""
        checker = GitLabContributorChecker(repo_path=self.temp_dir)
        
        assert checker.gitlab_token == 'test-token'
        assert checker.project_id == '123'
        assert checker.mr_iid == '456'
        assert checker.target_branch_sha == 'abc123'
        assert checker.source_branch_sha == 'def456'
    
    @patch('requests.post')
    def test_post_mr_comment(self, mock_post):
        """Test posting MR comments."""
        mock_post.return_value = Mock(status_code=201)
        
        checker = GitLabContributorChecker(repo_path=self.temp_dir)
        missing_contributors = ['John Doe', 'Jane Smith']
        
        result = checker.post_mr_comment(missing_contributors)
        
        assert result is True
        mock_post.assert_called_once()


class TestCLI:
    """Test the CLI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cli_help(self):
        """Test CLI help output."""
        with pytest.raises(SystemExit) as exc_info:
            cli_main(['--help'])
        assert exc_info.value.code == 0
    
    def test_cli_basic_usage(self):
        """Test basic CLI usage."""
        # Create minimal test repository structure
        citation_content = """
cff-version: 1.2.0
title: "Test Project"
authors:
  - family-names: "Doe"
    given-names: "John"
"""
        citation_file = self.temp_dir / "CITATION.cff"
        citation_file.write_text(citation_content)
        
        with patch('contrib_checker.core.ContributorChecker.check_all_contributors') as mock_check:
            mock_check.return_value = (True, {'missing_overall': []})
            
            result = cli_main([
                '--repo-path', str(self.temp_dir),
                '--mode', 'warn'
            ])
            
            assert result == 0


class TestIntegration:
    """Integration tests for the full package."""
    
    def test_package_imports(self):
        """Test that all package components can be imported."""
        from contrib_checker import ContributorChecker
        from contrib_checker import GitHubContributorChecker
        from contrib_checker import GitLabContributorChecker
        from contrib_checker.cli import main
        
        assert ContributorChecker is not None
        assert GitHubContributorChecker is not None
        assert GitLabContributorChecker is not None
        assert main is not None
    
    def test_module_execution(self):
        """Test that modules can be executed."""
        # Test GitHub module
        result = subprocess.run([
            sys.executable, '-m', 'contrib_checker.github'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        # Should exit with some code (0 or 1) but not crash
        assert result.returncode in [0, 1]
        
        # Test GitLab module
        result = subprocess.run([
            sys.executable, '-m', 'contrib_checker.gitlab'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        # Should exit with some code (0 or 1) but not crash
        assert result.returncode in [0, 1]
    
    def test_cli_execution(self):
        """Test CLI execution."""
        result = subprocess.run([
            sys.executable, '-m', 'contrib_checker.cli', '--help'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        assert result.returncode == 0
        assert 'usage:' in result.stdout.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
