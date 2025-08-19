"""
Contributor Checker - A library to check if contributors are properly listed in metadata files.

This library provides functionality to check if all Git contributors are properly acknowledged
in CITATION.cff or codemeta.json files, with support for GitHub Actions and GitLab CI.
"""

__version__ = "1.0.0"
__author__ = "Thomas Vuillaume"

from .core import ContributorChecker
from .github import GitHubContributorChecker  
from .gitlab import GitLabContributorChecker

__all__ = [
    "ContributorChecker",
    "GitHubContributorChecker", 
    "GitLabContributorChecker"
]
