#!/usr/bin/env python3
"""Core contributor checker - platform independent.

This module provides the core functionality for checking contributors from git history
against metadata files (CITATION.cff and codemeta.json). It's designed to be used
by platform-specific wrappers (GitHub Actions, GitLab CI, etc.).
"""

import subprocess
import yaml
import json
import re
from pathlib import Path
from typing import Set, Dict, Any, Tuple


class ContributorChecker:
    """Core contributor checker functionality."""
    
    def __init__(self, repo_path: Path = None, config: Dict[str, Any] = None):
        """Initialize the contributor checker.
        
        Args:
            repo_path: Path to the repository root. Defaults to current directory.
            config: Configuration dictionary with ignore lists and mode.
        """
        self.repo_path = repo_path or Path('.')
        self.config = config or self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            'mode': 'warn',
            'ignore_emails': ['dependabot[bot]@users.noreply.github.com'],
            'ignore_logins': ['dependabot[bot]']
        }
    
    def _run_git(self, args: list) -> str:
        """Run git command and return output."""
        try:
            res = subprocess.run(
                ['git'] + args, 
                cwd=self.repo_path, 
                capture_output=True, 
                text=True, 
                check=True
            )
            return res.stdout
        except subprocess.CalledProcessError as e:
            print(f"git failed: {' '.join(e.cmd)} -> {e.stderr}")
            return ''
    
    def should_include_contributor(self, contributor: str) -> bool:
        """Check if a contributor should be included in the check."""
        # Check ignore_emails
        m = re.search(r'<([^>]+)>', contributor)
        if m and m.group(1) in self.config.get('ignore_emails', []):
            return False
        
        # Check ignore_logins
        ignore_logins = self.config.get('ignore_logins', [])
        for login in ignore_logins:
            if login.lower() in contributor.lower():
                return False
        
        # Built-in bot filtering
        lower = contributor.lower()
        if 'bot' in lower or 'dependabot' in lower:
            return False
        return True
    
    def get_contributors_from_range(self, base_sha: str, head_sha: str) -> Set[str]:
        """Get contributors from a specific commit range."""
        if not (base_sha and head_sha):
            print('Base and head SHAs not provided; returning empty set')
            return set()
        
        out = self._run_git([
            'log', '--use-mailmap', '--format=%aN <%aE>', 
            f'{base_sha}..{head_sha}'
        ])
        
        contributors = set()
        for line in out.splitlines():
            line = line.strip()
            if line and self.should_include_contributor(line):
                contributors.add(line)
        
        return contributors
    
    def get_all_contributors(self) -> Set[str]:
        """Get all contributors from repository history."""
        out = self._run_git(['log', '--use-mailmap', '--format=%aN <%aE>', '--all'])
        
        contributors = set()
        for line in out.splitlines():
            line = line.strip()
            if line and self.should_include_contributor(line):
                contributors.add(line)
        
        return contributors
    
    def parse_citation_cff(self) -> Set[str]:
        """Parse CITATION.cff file and extract contributors."""
        path = self.repo_path / 'CITATION.cff'
        if not path.exists():
            return set()
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            authors = data.get('authors', [])
            result = set()
            
            for a in authors:
                if isinstance(a, dict):
                    name = None
                    if 'given-names' in a and 'family-names' in a:
                        name = f"{a.get('given-names')} {a.get('family-names')}"
                    elif 'name' in a:
                        name = a.get('name')
                    
                    if name:
                        email = a.get('email')
                        if email:
                            result.add(f"{name} <{email}>")
                        else:
                            result.add(name)
                elif isinstance(a, str):
                    result.add(a)
            
            return result
        except Exception as e:
            print(f"Failed to parse CITATION.cff: {e}")
            return set()
    
    def parse_codemeta_json(self) -> Set[str]:
        """Parse codemeta.json file and extract contributors."""
        path = self.repo_path / 'codemeta.json'
        if not path.exists():
            return set()
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            result = set()
            for field in ['author', 'contributor', 'maintainer']:
                authors = data.get(field, [])
                if not isinstance(authors, list):
                    authors = [authors]
                
                for a in authors:
                    if isinstance(a, dict):
                        name = a.get('name') or (
                            a.get('givenName', '') + ' ' + a.get('familyName', '')
                        ).strip()
                        if name:
                            email = a.get('email')
                            if email:
                                result.add(f"{name} <{email}>")
                            else:
                                result.add(name)
                    elif isinstance(a, str):
                        result.add(a)
            
            return result
        except Exception as e:
            print(f"Failed to parse codemeta.json: {e}")
            return set()
    
    def normalize_contributor_name(self, s: str) -> str:
        """Normalize contributor name for comparison."""
        s = re.sub(r'<[^>]+>', '', s)
        return ' '.join(s.split()).lower()
    
    def find_missing_contributors(self, 
                                contributors: Set[str], 
                                metadata_contribs: Set[str]) -> Set[str]:
        """Find contributors missing from metadata."""
        meta_norm = {
            self.normalize_contributor_name(m): m 
            for m in metadata_contribs
        }
        missing = set()
        for contrib in contributors:
            if self.normalize_contributor_name(contrib) not in meta_norm:
                missing.add(contrib)
        return missing
    
    def check_contributors_detailed(self, 
                                  contributors: Set[str], 
                                  context_name: str = "commits") -> Tuple[bool, Dict[str, Any]]:
        """Check contributors against metadata files with detailed results.
        
        Args:
            contributors: Set of contributor strings to check
            context_name: Description of the contributor context (e.g., "PR commits", "MR commits")
        
        Returns:
            Tuple of (success: bool, results: dict with detailed information)
        """
        print(f'Found {len(contributors)} contributors in {context_name}')
        for c in sorted(contributors):
            print(f'  - {c}')
        
        # Check each metadata file separately
        citation_cff = self.parse_citation_cff()
        codemeta_json = self.parse_codemeta_json()
        
        print('\nChecking CITATION.cff:')
        if citation_cff:
            print(f'  Found {len(citation_cff)} contributors in CITATION.cff')
            for c in sorted(citation_cff):
                print(f'    - {c}')
            missing_citation = self.find_missing_contributors(contributors, citation_cff)
            if missing_citation:
                print(f'  Missing from CITATION.cff: {sorted(missing_citation)}')
            else:
                print(f'  All {context_name} contributors present in CITATION.cff')
        else:
            print('  CITATION.cff not found or empty')
            missing_citation = contributors.copy()
        
        print('\nChecking codemeta.json:')
        if codemeta_json:
            print(f'  Found {len(codemeta_json)} contributors in codemeta.json')
            for c in sorted(codemeta_json):
                print(f'    - {c}')
            missing_codemeta = self.find_missing_contributors(contributors, codemeta_json)
            if missing_codemeta:
                print(f'  Missing from codemeta.json: {sorted(missing_codemeta)}')
            else:
                print(f'  All {context_name} contributors present in codemeta.json')
        else:
            print('  codemeta.json not found or empty')
            missing_codemeta = contributors.copy()
        
        # Overall check (union of both files)
        metadata = citation_cff | codemeta_json
        missing_overall = self.find_missing_contributors(contributors, metadata)
        
        print('\nOverall result:')
        current_mode = self.config.get('mode', 'warn')
        print(f'Running in mode: {current_mode}')
        
        # Prepare detailed results
        results = {
            'contributors': contributors,
            'citation_cff': citation_cff,
            'codemeta_json': codemeta_json,
            'missing_citation': missing_citation,
            'missing_codemeta': missing_codemeta,
            'missing_overall': missing_overall,
            'metadata_combined': metadata,
            'mode': current_mode,
            'context_name': context_name
        }
        
        if missing_overall:
            print(f'Missing contributors (not in any metadata file): {sorted(missing_overall)}')
            # Return success/failure based on mode
            success = current_mode != 'fail'
            if success:
                print('Mode is "warn" - posting warning but not failing')
            else:
                print('Mode is "fail" - check failed')
        else:
            print(f'All {context_name} contributors present in at least one metadata file')
            success = True
        
        return success, results
    
    def check_range_contributors(self, base_sha: str, head_sha: str, 
                               context_name: str = "range commits") -> Tuple[bool, Dict[str, Any]]:
        """Check contributors from a specific commit range."""
        contributors = self.get_contributors_from_range(base_sha, head_sha)
        return self.check_contributors_detailed(contributors, context_name)
    
    def check_all_contributors(self) -> Tuple[bool, Dict[str, Any]]:
        """Check all repository contributors."""
        contributors = self.get_all_contributors()
        return self.check_contributors_detailed(contributors, "repository history")


def create_comment_body(missing: Set[str], platform: str = "PR") -> str:
    """Create a comment body for missing contributors.
    
    Args:
        missing: Set of missing contributor strings
        platform: Platform name ("PR", "MR", etc.)
    
    Returns:
        Formatted comment body
    """
    lines = '\n'.join(f"- {m}" for m in sorted(missing))
    return (
        f"⚠️ **Metadata check: contributors missing from citation files**\n\n"
        f"The following contributors from this {platform} are not listed in the metadata files:\n\n"
        f"{lines}\n\n"
        f"Next steps:\n"
        f"- Add them to `CITATION.cff` / `codemeta.json` or update `.mailmap` if these are aliases.\n"
    )
