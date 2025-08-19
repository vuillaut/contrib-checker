#!/usr/bin/env python3
"""
Version management utility for contrib-checker.

Usage:
    python scripts/update_version.py 1.0.1
    python scripts/update_version.py --show
"""

import argparse
import re
import sys
from pathlib import Path

def get_current_version():
    """Get the current version from __init__.py"""
    init_file = Path(__file__).parent.parent / "contrib_checker" / "__init__.py"
    content = init_file.read_text()
    match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    return None

def update_version(new_version):
    """Update version in both pyproject.toml and __init__.py"""
    
    # Update pyproject.toml
    pyproject_file = Path(__file__).parent.parent / "pyproject.toml"
    content = pyproject_file.read_text()
    content = re.sub(
        r'version = ["\'][^"\']+["\']',
        f'version = "{new_version}"',
        content
    )
    pyproject_file.write_text(content)
    print(f"✅ Updated pyproject.toml to version {new_version}")
    
    # Update __init__.py
    init_file = Path(__file__).parent.parent / "contrib_checker" / "__init__.py"
    content = init_file.read_text()
    content = re.sub(
        r'__version__ = ["\'][^"\']+["\']',
        f'__version__ = "{new_version}"',
        content
    )
    init_file.write_text(content)
    print(f"✅ Updated __init__.py to version {new_version}")

def validate_version(version):
    """Validate version format (semantic versioning)"""
    pattern = r'^\d+\.\d+\.\d+(?:[-.]?(?:alpha|beta|rc|dev)\d*)?$'
    return re.match(pattern, version) is not None

def main():
    parser = argparse.ArgumentParser(description="Manage contrib-checker version")
    parser.add_argument("version", nargs="?", help="New version to set")
    parser.add_argument("--show", action="store_true", help="Show current version")
    
    args = parser.parse_args()
    
    if args.show:
        current = get_current_version()
        if current:
            print(f"Current version: {current}")
        else:
            print("❌ Could not determine current version")
            sys.exit(1)
        return
    
    if not args.version:
        current = get_current_version()
        print(f"Current version: {current}")
        print("Usage: python scripts/update_version.py <new_version>")
        print("Example: python scripts/update_version.py 1.0.1")
        return
    
    new_version = args.version
    
    if not validate_version(new_version):
        print(f"❌ Invalid version format: {new_version}")
        print("Expected format: X.Y.Z (semantic versioning)")
        sys.exit(1)
    
    current = get_current_version()
    print(f"Updating version from {current} to {new_version}")
    
    try:
        update_version(new_version)
        print("\n🎉 Version updated successfully!")
        print("\nNext steps:")
        print(f"1. Commit the changes: git add -A && git commit -m 'Bump version to {new_version}'")
        print(f"2. Create and push tag: git tag v{new_version} && git push origin v{new_version}")
        print("3. Create GitHub release from the tag to trigger PyPI publication")
    except Exception as e:
        print(f"❌ Error updating version: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
