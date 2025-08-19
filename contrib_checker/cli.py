"""Command-line interface for contrib-checker."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .core import ContributorChecker


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Check if Git contributors are properly listed in metadata files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check all contributors in current repository
  contrib-checker

  # Check contributors with specific mode
  contrib-checker --mode fail

  # Check contributors with ignore lists
  contrib-checker --ignore-emails bot@example.com --ignore-logins bot-user

  # Check specific commit range
  contrib-checker --from-sha abc123 --to-sha def456

  # Use specific repository path
  contrib-checker --repo-path /path/to/repo
        """
    )
    
    parser.add_argument(
        '--repo-path',
        type=Path,
        default=Path('.'),
        help='Path to the repository root (default: current directory)'
    )
    
    parser.add_argument(
        '--mode',
        choices=['warn', 'fail'],
        default='warn',
        help='Behavior mode: warn (default) or fail. In fail mode, exits with error code if contributors are missing'
    )
    
    parser.add_argument(
        '--ignore-emails',
        action='append',
        help='Email addresses to ignore (can be used multiple times)'
    )
    
    parser.add_argument(
        '--ignore-logins', 
        action='append',
        help='Login names to ignore (can be used multiple times)'
    )
    
    parser.add_argument(
        '--from-sha',
        help='Start commit SHA for range checking (requires --to-sha)'
    )
    
    parser.add_argument(
        '--to-sha',
        help='End commit SHA for range checking (requires --from-sha)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser


def main(args: Optional[list] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    # Build configuration
    config = {
        'mode': parsed_args.mode,
        'ignore_emails': parsed_args.ignore_emails or [],
        'ignore_logins': parsed_args.ignore_logins or []
    }
    
    # Initialize checker
    checker = ContributorChecker(
        repo_path=parsed_args.repo_path,
        config=config
    )
    
    try:
        # Check if we're doing range checking or all contributors
        if parsed_args.from_sha and parsed_args.to_sha:
            if parsed_args.verbose:
                print(f'Checking contributors from {parsed_args.from_sha} to {parsed_args.to_sha}')
            success, results = checker.check_range_contributors(
                parsed_args.from_sha,
                parsed_args.to_sha,
                "specified range"
            )
        elif parsed_args.from_sha or parsed_args.to_sha:
            print('Error: Both --from-sha and --to-sha must be provided for range checking')
            return 1
        else:
            if parsed_args.verbose:
                print('Checking all repository contributors')
            success, results = checker.check_all_contributors()
        
        # In warn mode, always return 0
        # In fail mode, return 1 if there are missing contributors
        if parsed_args.mode == 'fail' and not success:
            return 1
        
        return 0
        
    except Exception as e:
        print(f'Error: {e}')
        if parsed_args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
