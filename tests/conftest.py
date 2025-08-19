"""
Pytest configuration and fixtures for contrib-checker tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_repo():
    """Create a temporary directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_citation_cff():
    """Sample CITATION.cff content for testing."""
    return """
cff-version: 1.2.0
title: "Test Project"
message: "If you use this software, please cite it as below."
authors:
  - family-names: "Doe"
    given-names: "John"
    email: "john@example.com"
    orcid: "https://orcid.org/0000-0000-0000-0000"
  - family-names: "Smith"
    given-names: "Jane"
    email: "jane@example.com"
  - name: "Bot User"
    email: "bot@example.com"
"""


@pytest.fixture
def sample_codemeta_json():
    """Sample codemeta.json content for testing."""
    return """
{
  "@context": "https://doi.org/10.5063/schema/codemeta-2.0",
  "@type": "SoftwareSourceCode",
  "name": "Test Project",
  "author": [
    {
      "@type": "Person",
      "givenName": "John",
      "familyName": "Doe",
      "email": "john@example.com"
    },
    {
      "@type": "Person", 
      "givenName": "Jane",
      "familyName": "Smith",
      "email": "jane@example.com"
    }
  ],
  "contributor": [
    {
      "@type": "Person",
      "givenName": "Bob",
      "familyName": "Wilson",
      "email": "bob@example.com"
    }
  ]
}
"""


@pytest.fixture
def sample_mailmap():
    """Sample .mailmap content for testing."""
    return """
# Map multiple emails to canonical names
John Doe <john@example.com> <j.doe@company.com>
John Doe <john@example.com> <john.doe@university.edu>
Jane Smith <jane@example.com> <j.smith@oldcompany.com>
"""
