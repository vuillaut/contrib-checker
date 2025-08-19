"""
Unit tests for GitLab-specific functionality.
"""

import os
from unittest.mock import Mock, patch

from contrib_checker.gitlab import GitLabContributorChecker


class TestGitLabContributorChecker:
    """Test GitLab-specific functionality."""
    
    def test_initialization_with_env_vars(self, temp_repo):
        """Test initialization with GitLab environment variables."""
        with patch.dict(os.environ, {
            'GITLAB_TOKEN': 'test-token',
            'CI_PROJECT_ID': '123',
            'CI_PROJECT_URL': 'https://gitlab.com/owner/repo',
            'CI_MERGE_REQUEST_IID': '456',
            'CI_MERGE_REQUEST_TARGET_BRANCH_SHA': 'target-sha',
            'CI_COMMIT_SHA': 'source-sha',
            'CI_API_V4_URL': 'https://gitlab.com/api/v4',
            'MODE': 'fail',
            'IGNORE_EMAILS': 'bot1@example.com,bot2@example.com',
            'IGNORE_LOGINS': 'bot1,bot2'
        }):
            checker = GitLabContributorChecker(repo_path=temp_repo)
            
            assert checker.gitlab_token == 'test-token'
            assert checker.project_id == '123'
            assert checker.project_url == 'https://gitlab.com/owner/repo'
            assert checker.mr_iid == '456'
            assert checker.target_branch_sha == 'target-sha'
            assert checker.source_branch_sha == 'source-sha'
            assert checker.gitlab_api_url == 'https://gitlab.com/api/v4'
            assert checker.config['mode'] == 'fail'
            assert checker.config['ignore_emails'] == ['bot1@example.com', 'bot2@example.com']
            assert checker.config['ignore_logins'] == ['bot1', 'bot2']
    
    def test_default_api_url(self, temp_repo):
        """Test default GitLab API URL when not specified."""
        with patch.dict(os.environ, {
            'GITLAB_TOKEN': 'test-token',
            'CI_PROJECT_ID': '123'
        }, clear=True):
            checker = GitLabContributorChecker(repo_path=temp_repo)
            
            assert checker.gitlab_api_url == 'https://gitlab.com/api/v4'
    
    def test_config_loading(self, temp_repo):
        """Test configuration loading from environment variables."""
        with patch.dict(os.environ, {
            'MODE': 'warn',
            'IGNORE_EMAILS': 'ci@example.com,  build@example.com  ',  # Test whitespace handling
            'IGNORE_LOGINS': 'ci-bot,  build-bot  '  # Test whitespace handling
        }):
            checker = GitLabContributorChecker(repo_path=temp_repo)
            
            assert checker.config['mode'] == 'warn'
            assert checker.config['ignore_emails'] == ['ci@example.com', 'build@example.com']
            assert checker.config['ignore_logins'] == ['ci-bot', 'build-bot']
    
    def test_config_defaults(self, temp_repo):
        """Test default configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            checker = GitLabContributorChecker(repo_path=temp_repo)
            
            assert checker.config['mode'] == 'warn'
            assert 'dependabot[bot]@users.noreply.github.com' in checker.config['ignore_emails']
            assert 'noreply@gitlab.com' in checker.config['ignore_emails']
            assert 'dependabot[bot]' in checker.config['ignore_logins']
            assert 'gitlab-bot' in checker.config['ignore_logins']
    
    @patch('requests.post')
    def test_post_mr_comment_success(self, mock_post, temp_repo):
        """Test successful MR comment posting."""
        mock_post.return_value = Mock(status_code=201)
        
        with patch.dict(os.environ, {
            'GITLAB_TOKEN': 'test-token',
            'CI_PROJECT_ID': '123',
            'CI_MERGE_REQUEST_IID': '456',
            'CI_API_V4_URL': 'https://gitlab.example.com/api/v4'
        }):
            checker = GitLabContributorChecker(repo_path=temp_repo)
            missing_contributors = ['John Doe <john@example.com>', 'Jane Smith <jane@example.com>']
            
            result = checker.post_mr_comment(missing_contributors)
            
            assert result is True
            mock_post.assert_called_once()
            
            # Verify API call details
            call_args = mock_post.call_args
            expected_url = 'https://gitlab.example.com/api/v4/projects/123/merge_requests/456/notes'
            assert call_args[0][0] == expected_url
            assert 'Authorization' in call_args[1]['headers']
            assert call_args[1]['headers']['Authorization'] == 'Bearer test-token'
            assert call_args[1]['headers']['Content-Type'] == 'application/json'
            assert 'body' in call_args[1]['json']
    
    @patch('requests.post')
    def test_post_mr_comment_failure(self, mock_post, temp_repo):
        """Test MR comment posting failure."""
        mock_post.return_value = Mock(status_code=403, text='Forbidden')
        mock_post.return_value.raise_for_status.side_effect = Exception('HTTP 403')
        
        with patch.dict(os.environ, {
            'GITLAB_TOKEN': 'test-token',
            'CI_PROJECT_ID': '123',
            'CI_MERGE_REQUEST_IID': '456'
        }):
            checker = GitLabContributorChecker(repo_path=temp_repo)
            missing_contributors = ['John Doe <john@example.com>']
            
            result = checker.post_mr_comment(missing_contributors)
            
            assert result is False
    
    def test_post_mr_comment_missing_env(self, temp_repo):
        """Test MR comment posting with missing environment variables."""
        # Missing some required environment variables
        with patch.dict(os.environ, {'GITLAB_TOKEN': 'test-token'}, clear=True):
            checker = GitLabContributorChecker(repo_path=temp_repo)
            missing_contributors = ['John Doe <john@example.com>']
            
            result = checker.post_mr_comment(missing_contributors)
            
            assert result is False
    
    def test_post_mr_comment_no_requests(self, temp_repo):
        """Test MR comment posting when requests is not available."""
        with patch.dict(os.environ, {
            'GITLAB_TOKEN': 'test-token',
            'CI_PROJECT_ID': '123',
            'CI_MERGE_REQUEST_IID': '456'
        }):
            # Mock requests not being available
            with patch('contrib_checker.gitlab.requests', None):
                checker = GitLabContributorChecker(repo_path=temp_repo)
                missing_contributors = ['John Doe <john@example.com>']
                
                result = checker.post_mr_comment(missing_contributors)
                
                assert result is False
    
    def test_check_mr_contributors(self, temp_repo):
        """Test checking MR contributors."""
        with patch.dict(os.environ, {
            'GITLAB_TOKEN': 'test-token',
            'CI_PROJECT_ID': '123',
            'CI_MERGE_REQUEST_IID': '456',
            'CI_MERGE_REQUEST_TARGET_BRANCH_SHA': 'target-sha',
            'CI_COMMIT_SHA': 'source-sha'
        }):
            checker = GitLabContributorChecker(repo_path=temp_repo)
            
            # Mock the core checker
            with patch.object(checker.core_checker, 'check_range_contributors') as mock_check:
                mock_check.return_value = (True, {'missing_overall': []})
                
                result = checker.check_mr_contributors()
                
                assert result is True
                mock_check.assert_called_once_with('target-sha', 'source-sha', 'MR commits')
    
    def test_check_mr_contributors_with_missing(self, temp_repo):
        """Test checking MR contributors with missing contributors."""
        with patch.dict(os.environ, {
            'GITLAB_TOKEN': 'test-token',
            'CI_PROJECT_ID': '123',
            'CI_MERGE_REQUEST_IID': '456',
            'CI_MERGE_REQUEST_TARGET_BRANCH_SHA': 'target-sha',
            'CI_COMMIT_SHA': 'source-sha'
        }):
            checker = GitLabContributorChecker(repo_path=temp_repo)
            
            # Mock the core checker to return missing contributors
            missing_contributors = ['John Doe <john@example.com>']
            with patch.object(checker.core_checker, 'check_range_contributors') as mock_check:
                mock_check.return_value = (False, {'missing_overall': missing_contributors})
                
                # Mock comment posting
                with patch.object(checker, 'post_mr_comment', return_value=True) as mock_comment:
                    result = checker.check_mr_contributors()
                    
                    assert result is False
                    mock_comment.assert_called_once_with(missing_contributors)
    
    def test_check_all_contributors(self, temp_repo):
        """Test checking all repository contributors."""
        with patch.dict(os.environ, {}):
            checker = GitLabContributorChecker(repo_path=temp_repo)
            
            # Mock the core checker
            with patch.object(checker.core_checker, 'check_all_contributors') as mock_check:
                mock_check.return_value = (True, {'missing_overall': []})
                
                result = checker.check_all_contributors()
                
                assert result is True
                mock_check.assert_called_once()
    
    def test_mr_mode_detection(self, temp_repo):
        """Test MR mode detection based on environment variables."""
        # Test with full MR environment
        with patch.dict(os.environ, {
            'CI_MERGE_REQUEST_IID': '456',
            'CI_MERGE_REQUEST_TARGET_BRANCH_SHA': 'target-sha',
            'CI_COMMIT_SHA': 'source-sha'
        }):
            checker = GitLabContributorChecker(repo_path=temp_repo)
            
            # This would be used in the main() function to determine mode
            mr_mode = bool(checker.mr_iid and checker.target_branch_sha and checker.source_branch_sha)
            assert mr_mode is True
        
        # Test without MR environment
        with patch.dict(os.environ, {}, clear=True):
            checker = GitLabContributorChecker(repo_path=temp_repo)
            
            mr_mode = bool(checker.mr_iid and checker.target_branch_sha and checker.source_branch_sha)
            assert mr_mode is False
