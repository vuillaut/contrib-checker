# ContribChecker

ContribChecker is a GitHub Action and helper script that verifies that contributors who appear in the git history are listed in the repository metadata files (`CITATION.cff` and `codemeta.json`). It uses a `.mailmap` file to unify multiple emails/names for the same person.

Why this is useful
- Keeps citation and credit metadata accurate when new contributors add commits
- Helps projects maintain reproducible credit and citation information

What this repository provides
- A Python script at `check_contributors.py` that performs the check
- A GitHub Actions bot at `action.yml` that runs the script on PR events

How it works
- The action runs on PR events. It runs `git log --use-mailmap --format='%aN <%aE>' BASE..HEAD` to collect commit authors, so ensure `.mailmap` is present if you need to unify multiple emails.
- It compares commit authors against `CITATION.cff` and `codemeta.json` and posts a comment if missing contributors are found.
- If `mode: fail` is set in the config, the Action will fail the job (exit code 1).


## Quick start

1. Ensure your repository has `CITATION.cff` and/or `codemeta.json` with author/contributor entries.
2. Add a `.mailmap` at the repository root if you need to unify alternate emails or names from the git history.
3. Add this action (or copy the workflow) into your repo in `.github/workflows/contrib-check.yml`; the included workflow triggers on pull requests.


### Example `.github/workflows/contrib-check.yml`

```yaml
jobs:
  contrib-check:
    runs-on: ubuntu-latest
    
    steps:
      - name: Contrib metadata check
        uses: vuillaut/contrib-checker@main
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          mode: warn  # or 'fail' to make the workflow fail when contributors are missing
          ignore_emails: "dependabot[bot]@users.noreply.github.com,ci-bot@example.com,noreply@github.com"
          ignore_logins: "dependabot[bot],github-actions[bot],ci-bot"
```

## Requirements

- GitHub Actions must be enabled for your repository.
- A `CITATION.cff` or `codemeta.json` file must be present and properly formatted.
- Optional: A `.mailmap` file if you need to unify contributor names/emails from git history.