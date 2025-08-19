"""GitLab-specific contributor checker implementation."""

import os
import sys
from pathlib import Path
from typing import Dict, Any

try:
    import requests
except ImportError:
    requests = None

from .core import ContributorChecker, create_comment_body


class GitLabContributorChecker:
    """GitLab-specific wrapper for ContributorChecker."""
    
    def __init__(self, repo_path: Path = None) -> None:
        # GitLab CI environment variables
        self.gitlab_token = os.environ.get('GITLAB_TOKEN')
        self.project_id = os.environ.get('CI_PROJECT_ID')
        self.project_url = os.environ.get('CI_PROJECT_URL')
        self.mr_iid = os.environ.get('CI_MERGE_REQUEST_IID')
        self.target_branch_sha = os.environ.get('CI_MERGE_REQUEST_TARGET_BRANCH_SHA')
        self.source_branch_sha = os.environ.get('CI_COMMIT_SHA')
        self.gitlab_api_url = os.environ.get('CI_API_V4_URL', 'https://gitlab.com/api/v4')
        
        # Set default repo root
        if repo_path is None:
            repo_path = Path('.')
        
        # Load configuration
        self.config = self._load_config(repo_path)
        
        # Initialize core checker
        self.core_checker = ContributorChecker(
            repo_path=repo_path,
            config=self.config
        )
    
    def _load_config(self, repo_path: Path) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        default = {
            'mode': 'warn',
            'ignore_emails': ['dependabot[bot]@users.noreply.github.com', 'noreply@gitlab.com'],
            'ignore_logins': ['dependabot[bot]', 'gitlab-bot']
        }
        
        # Override with environment variables
        mode = os.environ.get('MODE', '').strip().lower()
        if mode in ['warn', 'fail']:
            default['mode'] = mode
            
        ignore_emails = os.environ.get('IGNORE_EMAILS', '').strip()
        if ignore_emails:
            emails = [email.strip() for email in ignore_emails.split(',') if email.strip()]
            default['ignore_emails'] = emails
            
        ignore_logins = os.environ.get('IGNORE_LOGINS', '').strip()
        if ignore_logins:
            logins = [login.strip() for login in ignore_logins.split(',') if login.strip()]
            default['ignore_logins'] = logins
            
        return default
    
    def post_mr_comment(self, missing_contributors) -> bool:
        """Post a comment on the GitLab merge request."""
        if not requests:
            print('requests not installed; skipping comment post')
            return False
        
        print(f'GitLab token present: {bool(self.gitlab_token)}')
        print(f'Project ID: {self.project_id}')
        print(f'MR IID: {self.mr_iid}')
        
        if not (self.gitlab_token and self.project_id and self.mr_iid):
            print('Missing GitLab env variables; cannot post comment')
            print('Required: GITLAB_TOKEN, CI_PROJECT_ID, CI_MERGE_REQUEST_IID')
            return False
        
        url = f"{self.gitlab_api_url}/projects/{self.project_id}/merge_requests/{self.mr_iid}/notes"
        headers = {
            'Authorization': f'Bearer {self.gitlab_token}',
            'Content-Type': 'application/json'
        }
        
        print(f'Posting comment to: {url}')
        
        try:
            comment_body = create_comment_body(missing_contributors, "MR")
            response = requests.post(
                url,
                headers=headers,
                json={'body': comment_body}
            )
            print(f'Response status: {response.status_code}')
            if response.status_code not in [200, 201]:
                print(f'Response body: {response.text}')
            response.raise_for_status()
            print('Posted MR comment successfully')
            return True
        except Exception as e:
            print(f'Failed to post MR comment: {e}')
            if hasattr(e, 'response'):
                print(f'Response status: {e.response.status_code}')
                print(f'Response body: {e.response.text}')
            return False
    
    def check_mr_contributors(self) -> bool:
        """Check MR contributors against metadata files."""
        success, results = self.core_checker.check_range_contributors(
            self.target_branch_sha, 
            self.source_branch_sha, 
            "MR commits"
        )
        
        # Post comment if there are missing contributors
        if results['missing_overall']:
            print('Attempting to post MR comment...')
            comment_posted = self.post_mr_comment(results['missing_overall'])
            if not comment_posted:
                print('Failed to post MR comment - check GitLab token and permissions')
        
        return success
    
    def check_all_contributors(self) -> bool:
        """Check all repository contributors against metadata files."""
        success, results = self.core_checker.check_all_contributors()
        return success


def main() -> None:
    """Main function to run the GitLab contributor checker."""
    checker = GitLabContributorChecker()
    
    # Determine if we're in MR mode or test mode
    mr_mode = bool(checker.mr_iid and checker.target_branch_sha and checker.source_branch_sha)
    
    try:
        if mr_mode:
            print('Running in GitLab MR mode')
            ok = checker.check_mr_contributors()
        else:
            print('Running in test mode (checking all contributors)')
            ok = checker.check_all_contributors()
        
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
