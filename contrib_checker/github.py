"""GitHub-specific contributor checker implementation."""

import os
import sys
from pathlib import Path
from typing import Dict, Any

try:
    import requests
except ImportError:
    requests = None

from .core import ContributorChecker, create_comment_body


class GitHubContributorChecker:
    """GitHub-specific wrapper for ContributorChecker."""
    
    def __init__(self, repo_path: Path = None) -> None:
        # GitHub environment variables
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.github_repo = os.environ.get('GITHUB_REPOSITORY')
        self.pr_number = os.environ.get('PR_NUMBER')
        self.pr_base_sha = os.environ.get('PR_BASE_SHA')
        self.pr_head_sha = os.environ.get('PR_HEAD_SHA')
        
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
        """Load configuration from file and environment variables."""
        import yaml
        
        cfg_path = repo_path / '.github' / 'contrib-metadata-check.yml'
        default = {
            'mode': 'warn',
            'ignore_emails': ['dependabot[bot]@users.noreply.github.com'],
            'ignore_logins': ['dependabot[bot]']
        }
        
        # Load from config file if it exists
        if cfg_path.exists():
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                    default.update(data)
            except Exception as e:
                print(f"Warning loading config: {e}")
        
        # Override with action inputs if provided
        action_mode = os.environ.get('ACTION_MODE')
        if action_mode:
            default['mode'] = action_mode
            
        action_ignore_emails = os.environ.get('ACTION_IGNORE_EMAILS', '').strip()
        if action_ignore_emails:
            emails = [email.strip() for email in action_ignore_emails.split(',') if email.strip()]
            default['ignore_emails'] = emails
            
        action_ignore_logins = os.environ.get('ACTION_IGNORE_LOGINS', '').strip()
        if action_ignore_logins:
            logins = [login.strip() for login in action_ignore_logins.split(',') if login.strip()]
            default['ignore_logins'] = logins
            
        return default
    
    def post_pr_comment(self, missing_contributors) -> bool:
        """Post a comment on the GitHub pull request."""
        if not requests:
            print('requests not installed; skipping post')
            return False
        
        print(f'GitHub token present: {bool(self.github_token)}')
        print(f'GitHub repo: {self.github_repo}')
        print(f'PR number: {self.pr_number}')
        
        if not (self.github_token and self.github_repo and self.pr_number):
            print('Missing GitHub env variables; cannot post comment')
            print('Required env vars: GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER')
            return False
        
        url = f"https://api.github.com/repos/{self.github_repo}/issues/{self.pr_number}/comments"
        headers = {
            'Authorization': f'token {self.github_token}', 
            'Accept': 'application/vnd.github.v3+json'
        }
        
        print(f'Posting comment to: {url}')
        
        try:
            comment_body = create_comment_body(missing_contributors, "PR")
            r = requests.post(url, headers=headers, json={'body': comment_body})
            print(f'Response status: {r.status_code}')
            if r.status_code != 201:
                print(f'Response body: {r.text}')
            r.raise_for_status()
            print('Posted PR comment successfully')
            return True
        except Exception as e:
            print(f'Failed to post PR comment: {e}')
            if hasattr(e, 'response'):
                print(f'Response status: {e.response.status_code}')
                print(f'Response body: {e.response.text}')
            return False
    
    def check_pr_contributors(self) -> bool:
        """Check PR contributors against metadata files."""
        success, results = self.core_checker.check_range_contributors(
            self.pr_base_sha, 
            self.pr_head_sha, 
            "PR commits"
        )
        
        # Post comment if there are missing contributors
        if results['missing_overall']:
            print('Attempting to post PR comment...')
            comment_posted = self.post_pr_comment(results['missing_overall'])
            if not comment_posted:
                print('Failed to post PR comment - check GitHub token and permissions')
        
        return success
    
    def check_all_contributors(self) -> bool:
        """Check all repository contributors against metadata files."""
        success, results = self.core_checker.check_all_contributors()
        return success


def main() -> None:
    """Main function to run the GitHub contributor checker."""
    checker = GitHubContributorChecker()
    
    # Determine if we're in PR mode or test mode
    pr_mode = bool(checker.pr_base_sha and checker.pr_head_sha and checker.pr_number)
    
    try:
        if pr_mode:
            print('Running in GitHub PR mode')
            ok = checker.check_pr_contributors()
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
