
# Contributing

Thanks for helping improve contrib-checker — keep changes small and focused.

## How to contribute

- Fork the repository and create a feature branch from `main`.
- If you want to make a significant change or propose a new feature, consider discussing it first in an issue.
- Open a clear, scoped pull request describing what changed and why.

## Code style

- Python: follow PEP8. Use small, well-named functions and clear variable names.
- Keep dependencies minimal; document new deps in `README.md`.

## Tests & validation

- Add or update tests for new behavior. Run the local test harness:

```bash
python3 .github/test_contributor_check.py
```

- Check for syntax errors:

```bash
python3 -m py_compile <path-to-file>
```

## Config & workflows

- Changes to `.github/workflows/*` or action manifests must include a short description and, if needed, a sample `.github/contrib-metadata-check.yml`.

## Behavioral changes

- If you change comment/failure behavior, document how maintainers are notified and how users can opt out via `.github/contrib-metadata-check.yml`.

## Review

- PRs are reviewed by maintainers. Address review comments and squash commits when requested.

## License

- By contributing you agree your changes will be licensed under the repository license.

Thanks — your contributions are appreciated.
