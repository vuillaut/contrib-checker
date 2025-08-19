"""
Unit tests for GitHub-specific functionality.
"""

import os
from unittest.mock import Mock, patch

from contrib_checker.github import GitHubContributorChecker


class TestGitHubContributorChecker:
    """Test GitHub-specific functionality."""
    
    def test_initialization_with_env_vars(self, temp_repo):
        """Test initialization with GitHub environment variables."""
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_REPOSITORY': 'owner/repo',
            'PR_NUMBER': '123',
            'PR_BASE_SHA': 'base-sha',
            'PR_HEAD_SHA': 'head-sha',
            'ACTION_MODE': 'fail',
            'ACTION_IGNORE_EMAILS': 'bot1@example.com,bot2@example.com',
            'ACTION_IGNORE_LOGINS': 'bot1,bot2'
        }):
            checker = GitHubContributorChecker(repo_path=temp_repo)
            
            assert checker.github_token == 'test-token'
            assert checker.github_repo == 'owner/repo'
            assert checker.pr_number == '123'
            assert checker.pr_base_sha == 'base-sha'
            assert checker.pr_head_sha == 'head-sha'
            assert checker.config['mode'] == 'fail'
            assert checker.config['ignore_emails'] == ['bot1@example.com', 'bot2@example.com']
            assert checker.config['ignore_logins'] == ['bot1', 'bot2']
    
    def test_load_config_from_file(self, temp_repo):
        """Test loading configuration from .github/contrib-metadata-check.yml."""
        # Create config file
        config_dir = temp_repo / '.github'
        config_dir.mkdir()
        config_file = config_dir / 'contrib-metadata-check.yml'
        config_content = """
mode: fail
ignore_emails:
  - config-bot@example.com
ignore_logins:
  - config-bot
"""
        config_file.write_text(config_content)
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_REPOSITORY': 'owner/repo'
        }):
            checker = GitHubContributorChecker(repo_path=temp_repo)
            
            assert checker.config['mode'] == 'fail'
            assert 'config-bot@example.com' in checker.config['ignore_emails']
            assert 'config-bot' in checker.config['ignore_logins']
    
    def test_config_env_override_file(self, temp_repo):
        """Test that environment variables override config file."""
        # Create config file with some settings
        config_dir = temp_repo / '.github'
        config_dir.mkdir()
        config_file = config_dir / 'contrib-metadata-check.yml'
        config_content = """
mode: warn
ignore_emails:
  - file-bot@example.com
"""
        config_file.write_text(config_content)
        
        # Set environment variables that should override
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_REPOSITORY': 'owner/repo',
            'ACTION_MODE': 'fail',
            'ACTION_IGNORE_EMAILS': 'env-bot@example.com'
        }):
            checker = GitHubContributorChecker(repo_path=temp_repo)
            
            # Environment should override file
            assert checker.config['mode'] == 'fail'
            assert checker.config['ignore_emails'] == ['env-bot@example.com']
    
    @patch('requests.post')
    def test_post_pr_comment_success(self, mock_post, temp_repo):
        """Test successful PR comment posting."""
        mock_post.return_value = Mock(status_code=201)
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_REPOSITORY': 'owner/repo',
            'PR_NUMBER': '123'
        }):
            checker = GitHubContributorChecker(repo_path=temp_repo)
            missing_contributors = ['John Doe <john@example.com>', 'Jane Smith <jane@example.com>']
            
            result = checker.post_pr_comment(missing_contributors)
            
            assert result is True
            mock_post.assert_called_once()
            
            # Verify API call details
            call_args = mock_post.call_args
            assert call_args[0][0] == 'https://api.github.com/repos/owner/repo/issues/123/comments'
            assert 'Authorization' in call_args[1]['headers']
            assert call_args[1]['headers']['Authorization'] == 'token test-token'
            assert 'body' in call_args[1]['json']
    
    @patch('requests.post')
    def test_post_pr_comment_failure(self, mock_post, temp_repo):
        """Test PR comment posting failure."""
        mock_post.return_value = Mock(status_code=403, text='Forbidden')
        mock_post.return_value.raise_for_status.side_effect = Exception('HTTP 403')
        
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_REPOSITORY': 'owner/repo',
            'PR_NUMBER': '123'
        }):
            checker = GitHubContributorChecker(repo_path=temp_repo)
            missing_contributors = ['John Doe <john@example.com>']
            
            result = checker.post_pr_comment(missing_contributors)
            
            assert result is False
    
    def test_post_pr_comment_missing_env(self, temp_repo):
        """Test PR comment posting with missing environment variables."""
        # Missing some required environment variables
        with patch.dict(os.environ, {'GITHUB_TOKEN': 'test-token'}, clear=True):
            checker = GitHubContributorChecker(repo_path=temp_repo)
            missing_contributors = ['John Doe <john@example.com>']
            
            result = checker.post_pr_comment(missing_contributors)
            
            assert result is False
    
    @patch('requests.post', side_effect=ImportError())
    def test_post_pr_comment_no_requests(self, mock_post, temp_repo):
        """Test PR comment posting when requests is not available."""
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_REPOSITORY': 'owner/repo',
            'PR_NUMBER': '123'
        }):
            # Mock requests not being available
            with patch('contrib_checker.github.requests', None):
                checker = GitHubContributorChecker(repo_path=temp_repo)
                missing_contributors = ['John Doe <john@example.com>']
                
                result = checker.post_pr_comment(missing_contributors)
                
                assert result is False
    
    def test_check_pr_contributors(self, temp_repo):
        """Test checking PR contributors."""
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_REPOSITORY': 'owner/repo',
            'PR_NUMBER': '123',
            'PR_BASE_SHA': 'base-sha',
            'PR_HEAD_SHA': 'head-sha'
        }):
            checker = GitHubContributorChecker(repo_path=temp_repo)
            
            # Mock the core checker
            with patch.object(checker.core_checker, 'check_range_contributors') as mock_check:
                mock_check.return_value = (True, {'missing_overall': []})
                
                result = checker.check_pr_contributors()
                
                assert result is True
                mock_check.assert_called_once_with('base-sha', 'head-sha', 'PR commits')
    
    def test_check_pr_contributors_with_missing(self, temp_repo):
        """Test checking PR contributors with missing contributors."""
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_REPOSITORY': 'owner/repo',
            'PR_NUMBER': '123',
            'PR_BASE_SHA': 'base-sha',
            'PR_HEAD_SHA': 'head-sha'
        }):
            checker = GitHubContributorChecker(repo_path=temp_repo)
            
            # Mock the core checker to return missing contributors
            missing_contributors = ['John Doe <john@example.com>']
            with patch.object(checker.core_checker, 'check_range_contributors') as mock_check:
                mock_check.return_value = (False, {'missing_overall': missing_contributors})
                
                # Mock comment posting
                with patch.object(checker, 'post_pr_comment', return_value=True) as mock_comment:
                    result = checker.check_pr_contributors()
                    
                    assert result is False
                    mock_comment.assert_called_once_with(missing_contributors)
    
    def test_check_all_contributors(self, temp_repo):
        """Test checking all repository contributors."""
        with patch.dict(os.environ, {
            'GITHUB_TOKEN': 'test-token',
            'GITHUB_REPOSITORY': 'owner/repo'
        }):
            checker = GitHubContributorChecker(repo_path=temp_repo)
            
            # Mock the core checker
            with patch.object(checker.core_checker, 'check_all_contributors') as mock_check:
                mock_check.return_value = (True, {'missing_overall': []})
                
                result = checker.check_all_contributors()
                
                assert result is True
                mock_check.assert_called_once()
