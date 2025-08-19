# contrib-checker

contrib-checker checks if code contributors are properly listed in metadata files such as `CITATION.cff` and `codemeta.json` based on the git history.

It provides:

- **Python library**: Installable package for programmatic use
- **Command-line tool**: `contrib-checker` CLI for local checking
- **GitHub Action**: Automated checking in GitHub workflows 
- **GitLab CI**: Support for GitLab merge request checking

## Installation

### As a Python package

```bash
pip install contrib-checker
```

### For development

```bash
git clone https://github.com/vuillaut/contrib-checker.git
cd contrib-checker
pip install -e .

```

## Usage

### Command-line tool

After installation, you can use the `contrib-checker` command:

```bash
# Check all contributors in current repository
contrib-checker

# Check with specific mode
contrib-checker --mode fail

# Check with ignore lists
contrib-checker --ignore-emails bot@example.com --ignore-logins bot-user

# Check specific commit range
contrib-checker --from-sha abc123 --to-sha def456

# Use specific repository path
contrib-checker --repo-path /path/to/repo

# See all options
contrib-checker --help
```

### As a Python library

```python
from contrib_checker import ContributorChecker
from pathlib import Path

# Initialize checker
config = {
    'mode': 'warn',  # or 'fail'
    'ignore_emails': ['bot@example.com'],
    'ignore_logins': ['bot-user']
}

checker = ContributorChecker(
    repo_path=Path('.'),
    config=config
)

# Check all contributors
success, results = checker.check_all_contributors()

# Check specific commit range
success, results = checker.check_range_contributors(
    from_sha='abc123',
    to_sha='def456', 
    description='PR commits'
)

# Check results
if results['missing_overall']:
    print("Missing contributors:")
    for contributor in results['missing_overall']:
        print(f"  {contributor}")
```

### Platform-specific usage

```python
# GitHub-specific wrapper
from contrib_checker import GitHubContributorChecker

github_checker = GitHubContributorChecker()
success = github_checker.check_pr_contributors()

# GitLab-specific wrapper  
from contrib_checker import GitLabContributorChecker

gitlab_checker = GitLabContributorChecker()
success = gitlab_checker.check_mr_contributors()
```

## GitHub Action Setup

### Quick start

1. Ensure your repository has `CITATION.cff` and/or `codemeta.json` with author/contributor entries.
2. Add a `.mailmap` at the repository root if you need to unify alternate emails or names from the git history.
3. Add this action (or copy the workflow) into your repo in `.github/workflows/contrib-check.yml`; the included workflow triggers on pull requests.


### Example `.github/workflows/contrib-check.yml`

```yaml
name: Contributor Check

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write # allows posting comments on PRs

jobs:
  contrib-check:
    runs-on: ubuntu-latest
    
    steps:
      - name: Contrib metadata check
        uses: vuillaut/contrib-checker@main
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          mode: warn  # or 'fail' to make the workflow fail when contributors are missing
          ignore_emails: "dependabot[bot]@users.noreply.github.com,ci-bot@example.com"
          ignore_logins: "dependabot[bot],github-actions[bot]"
```

## GitLab CI Setup

See [GITLAB_CI_USAGE.md](GITLAB_CI_USAGE.md) for detailed GitLab CI setup instructions.

### Example `.gitlab-ci.yml`

```yaml
contrib-check:
  stage: test
  image: python:3.11
  script:
    - pip install contrib-checker
    - contrib-checker
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

## How it works

- Uses `git log --use-mailmap` to collect commit authors, so ensure `.mailmap` is present if you need to unify multiple emails
- Compares commit authors against `CITATION.cff` and `codemeta.json` contributors
- Posts comments on GitHub PRs or GitLab MRs when missing contributors are found
- Can be configured to fail CI when contributors are missing (`mode: fail`)

## Requirements

- Python 3.8+
- Git repository with contributor metadata files
- For GitHub Actions: `CITATION.cff` or `codemeta.json` file
- For GitLab CI: Same metadata files plus GitLab API token
- Optional: `.mailmap` file to unify contributor names/emails

## Configuration

The tool can be configured via:

1. **Configuration file**: `.github/contrib-metadata-check.yml` (GitHub) or environment variables (GitLab)
2. **Command-line arguments**: When using the CLI
3. **Environment variables**: For CI/CD integration

### Configuration options

- `mode`: `warn` (default) or `fail`
- `ignore_emails`: List of email addresses to ignore
- `ignore_logins`: List of login names to ignore

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
