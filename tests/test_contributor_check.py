#!/usr/bin/env python3
"""Light test runner for contributor checker parsing functions.

Place this file in `.github` and run locally to exercise parsing and normalization
without reaching out to the GitHub API.
"""

import sys
import os
from pathlib import Path

# Ensure the script directory is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from check_contributors import ContributorChecker


def test_citation_parsing():
    print("Testing CITATION.cff parsing...")

    os.environ.update({
        'GITHUB_TOKEN': 'test-token',
        'GITHUB_REPOSITORY': 'test/repo',
        'PR_NUMBER': '1',
        'PR_BASE_SHA': 'base-sha',
        'PR_HEAD_SHA': 'head-sha'
    })

    checker = ContributorChecker()
    print(f"Config loaded: {checker.config}")

    citation_contributors = checker.parse_citation_cff()
    print(f"Found {len(citation_contributors)} contributors in CITATION.cff:")
    for contrib in sorted(citation_contributors):
        print(f"  - {contrib}")

    codemeta_contributors = checker.parse_codemeta_json()
    print(f"Found {len(codemeta_contributors)} contributors in codemeta.json:")
    for contrib in sorted(codemeta_contributors):
        print(f"  - {contrib}")

    test_contributors = [
        "Thomas Vuillaume <thomas.vuillaume@lapp.in2p3.fr>",
        "Thomas   Vuillaume   <different@email.com>",
        "THOMAS VUILLAUME"
    ]

    print("\nTesting name normalization:")
    for contrib in test_contributors:
        normalized = checker.normalize_contributor_name(contrib)
        print(f"  '{contrib}' -> '{normalized}'")

    return True


if __name__ == '__main__':
    try:
        test_citation_parsing()
        print("\n✅ Test run complete")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
