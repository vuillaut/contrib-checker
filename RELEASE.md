# Release Process for contrib-checker

This document outlines the process for releasing new versions of contrib-checker to PyPI.

## Prerequisites

1. **Repository Access**: Write access to the GitHub repository
2. **PyPI Trusted Publisher**: The repository should be configured as a trusted publisher on PyPI
3. **Clean Working Directory**: All changes committed and pushed to main branch

## Release Steps

### 1. Prepare the Release

#### Update Version
Use the version management script to update the version consistently:

```bash
# Check current version
python scripts/update_version.py --show

# Update to new version (example: 1.0.1)
python scripts/update_version.py 1.0.1
```

This will update both `pyproject.toml` and `contrib_checker/__init__.py`.

#### Update Changelog (Optional)
Update `CHANGELOG.md` or release notes with new features, bug fixes, and breaking changes.

#### Run Tests
Ensure all tests pass before releasing:

```bash
python -m pytest tests/ -v
```

### 2. Commit and Tag

```bash
# Commit version changes
git add -A
git commit -m "Bump version to 1.0.1"

# Create and push tag
git tag v1.0.1
git push origin main
git push origin v1.0.1
```

### 3. Create GitHub Release

1. Go to the [Releases page](https://github.com/vuillaut/contrib-checker/releases)
2. Click "Create a new release"
3. Select the tag you just created (v1.0.1)
4. Set release title (e.g., "contrib-checker v1.0.1")
5. Add release notes describing changes
6. Click "Publish release"

**The PyPI publication workflow will automatically trigger when the release is published.**

### 4. Verify Publication

1. **Check GitHub Actions**: Monitor the "Publish to PyPI" workflow
2. **Verify on PyPI**: Check that the new version appears on [PyPI](https://pypi.org/project/contrib-checker/)
3. **Test Installation**: 
   ```bash
   pip install --upgrade contrib-checker
   python -c "import contrib_checker; print(contrib_checker.__version__)"
   ```

## Manual Testing (Optional)

### Test PyPI Publication

You can test the publication process using TestPyPI before making a real release:

1. Go to GitHub Actions
2. Select "Publish to PyPI" workflow
3. Click "Run workflow"
4. Check "Publish to Test PyPI instead of PyPI"
5. Run the workflow

This will publish to [test.pypi.org](https://test.pypi.org/project/contrib-checker/) for testing.

### Install from TestPyPI

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ contrib-checker
```

## Workflow Details

The PyPI publication workflow (`.github/workflows/pypi.yml`) includes:

1. **Build**: Creates source distribution and wheel
2. **Test Installation**: Tests package installation on multiple Python versions
3. **Publish**: Uploads to PyPI (or TestPyPI) using trusted publishing
4. **Verify**: Confirms the package is available and installable from PyPI

## Troubleshooting

### Common Issues

1. **Version Already Exists**: PyPI doesn't allow overwriting existing versions. Increment the version number.

2. **Trusted Publisher Not Configured**: 
   - Go to PyPI project settings
   - Add GitHub as a trusted publisher
   - Configure: Owner: `vuillaut`, Repository: `contrib-checker`, Workflow: `pypi.yml`

3. **Test Failures**: Fix failing tests before proceeding with release.

4. **Permission Errors**: Ensure the GitHub token has necessary permissions.

### Manual Publication (Fallback)

If the automated workflow fails, you can publish manually:

```bash
# Build the package
python -m build

# Upload to PyPI (requires API token)
python -m twine upload dist/*
```

