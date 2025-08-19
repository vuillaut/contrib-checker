"""
Unit tests for the core ContributorChecker functionality.
"""

from unittest.mock import Mock, patch

from contrib_checker.core import ContributorChecker


class TestContributorCheckerCore:
    """Test core functionality with realistic scenarios."""
    
    def test_parse_citation_cff_comprehensive(self, temp_repo, sample_citation_cff):
        """Test comprehensive CITATION.cff parsing."""
        citation_file = temp_repo / "CITATION.cff"
        citation_file.write_text(sample_citation_cff)
        
        config = {'mode': 'warn', 'ignore_emails': [], 'ignore_logins': []}
        checker = ContributorChecker(repo_path=temp_repo, config=config)
        
        contributors = checker.parse_citation_cff()
        
        # Should find all authors with email format
        assert len(contributors) == 3
        assert "John Doe <john@example.com>" in contributors
        assert "Jane Smith <jane@example.com>" in contributors
        assert "Bot User <bot@example.com>" in contributors
    
    def test_parse_codemeta_json_comprehensive(self, temp_repo, sample_codemeta_json):
        """Test comprehensive codemeta.json parsing."""
        codemeta_file = temp_repo / "codemeta.json"
        codemeta_file.write_text(sample_codemeta_json)
        
        config = {'mode': 'warn', 'ignore_emails': [], 'ignore_logins': []}
        checker = ContributorChecker(repo_path=temp_repo, config=config)
        
        contributors = checker.parse_codemeta_json()
        
        # Should find authors and contributors with email format
        assert len(contributors) == 3
        assert "John Doe <john@example.com>" in contributors
        assert "Jane Smith <jane@example.com>" in contributors
        assert "Bob Wilson <bob@example.com>" in contributors
    
    def test_ignore_patterns(self, temp_repo, sample_citation_cff):
        """Test that ignore patterns work correctly."""
        citation_file = temp_repo / "CITATION.cff"
        citation_file.write_text(sample_citation_cff)
        
        config = {
            'mode': 'warn',
            'ignore_emails': ['bot@example.com'],
            'ignore_logins': ['bot-user']
        }
        checker = ContributorChecker(repo_path=temp_repo, config=config)
        
        # Test the filtering logic directly
        test_contributors = [
            "John Doe <john@example.com>",
            "Jane Smith <jane@example.com>", 
            "Bot User <bot@example.com>",  # Should be ignored due to email
            "dependabot[bot] <dependabot@users.noreply.github.com>",  # Should be ignored due to built-in pattern
            "github-actions[bot] <actions@github.com>"  # Should be ignored due to built-in pattern
        ]
        
        # Test each contributor individually
        assert checker.should_include_contributor("John Doe <john@example.com>")
        assert checker.should_include_contributor("Jane Smith <jane@example.com>")
        assert not checker.should_include_contributor("Bot User <bot@example.com>")  # ignored email
        assert not checker.should_include_contributor("dependabot[bot] <dependabot@users.noreply.github.com>")  # built-in bot
        assert not checker.should_include_contributor("github-actions[bot] <actions@github.com>")  # built-in bot
        
        # Test with actual range check by mocking git output instead
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="\n".join(test_contributors) + "\n"
            )
            
            contributors = checker.get_contributors_from_range("abc123", "def456")
            
            # Should only include non-ignored contributors
            assert len(contributors) == 2
            assert "John Doe <john@example.com>" in contributors
            assert "Jane Smith <jane@example.com>" in contributors
            assert "Bot User <bot@example.com>" not in contributors
            assert "dependabot[bot] <dependabot@users.noreply.github.com>" not in contributors
            assert "github-actions[bot] <actions@github.com>" not in contributors
    
    @patch('subprocess.run')
    def test_git_mailmap_usage(self, mock_run, temp_repo, sample_mailmap):
        """Test that git mailmap is used correctly."""
        mailmap_file = temp_repo / ".mailmap"
        mailmap_file.write_text(sample_mailmap)
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout="John Doe <john@example.com>\nJane Smith <jane@example.com>\n"
        )
        
        config = {'mode': 'warn', 'ignore_emails': [], 'ignore_logins': []}
        checker = ContributorChecker(repo_path=temp_repo, config=config)
        
        contributors = checker.get_contributors_from_range("abc123", "def456")
        
        # Verify git command includes --use-mailmap
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "--use-mailmap" in args
        
        assert len(contributors) == 2
        assert "John Doe <john@example.com>" in contributors
        assert "Jane Smith <jane@example.com>" in contributors
    
    def test_name_normalization_edge_cases(self, temp_repo):
        """Test name normalization with edge cases."""
        config = {'mode': 'warn', 'ignore_emails': [], 'ignore_logins': []}
        checker = ContributorChecker(repo_path=temp_repo, config=config)
        
        test_cases = [
            # Input, Expected output
            ("John Doe <john@example.com>", "john doe"),
            ("  John   Doe  ", "john doe"),
            ("JOHN DOE", "john doe"),
            ("john doe", "john doe"),
            ("Jean-Claude Van Damme", "jean-claude van damme"),
            ("O'Connor, Mary", "o'connor, mary"),
            ("José García", "josé garcía"),
            ("李小明", "李小明"),
            ("", ""),
            ("   ", ""),
            ("No-Email Person", "no-email person"),
            ("Person With Numbers123", "person with numbers123"),
        ]
        
        for input_name, expected in test_cases:
            result = checker.normalize_contributor_name(input_name)
            assert result == expected, f"Failed for '{input_name}': expected '{expected}', got '{result}'"
    
    def test_check_all_contributors_integration(self, temp_repo, sample_citation_cff):
        """Test full integration of checking all contributors."""
        # Create citation file
        citation_file = temp_repo / "CITATION.cff"
        citation_file.write_text(sample_citation_cff)
        
        config = {'mode': 'warn', 'ignore_emails': [], 'ignore_logins': []}
        checker = ContributorChecker(repo_path=temp_repo, config=config)
        
        # Mock git log to return some contributors
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="John Doe <john@example.com>\nMissing Person <missing@example.com>\n"
            )
            
            success, results = checker.check_all_contributors()
            
            # John Doe should be found, Missing Person should not
            assert len(results['missing_overall']) == 1
            assert "Missing Person <missing@example.com>" in results['missing_overall']
            
            # In warn mode, should still return success
            assert success is True
    
    def test_check_range_contributors_fail_mode(self, temp_repo):
        """Test that fail mode works correctly."""
        config = {'mode': 'fail', 'ignore_emails': [], 'ignore_logins': []}
        checker = ContributorChecker(repo_path=temp_repo, config=config)
        
        # Mock git log to return contributors not in any metadata file
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="Missing Person <missing@example.com>\n"
            )
            
            success, results = checker.check_range_contributors(
                "abc123", "def456", "test commits"
            )
            
            # Should fail because contributor is missing and mode is 'fail'
            assert success is False
            assert len(results['missing_overall']) == 1
    
    def test_empty_metadata_files(self, temp_repo):
        """Test behavior with empty or missing metadata files."""
        config = {'mode': 'warn', 'ignore_emails': [], 'ignore_logins': []}
        checker = ContributorChecker(repo_path=temp_repo, config=config)
        
        # No metadata files exist
        citation_contributors = checker.parse_citation_cff()
        codemeta_contributors = checker.parse_codemeta_json()
        
        assert len(citation_contributors) == 0
        assert len(codemeta_contributors) == 0
        
        # Create empty files
        (temp_repo / "CITATION.cff").write_text("")
        (temp_repo / "codemeta.json").write_text("{}")
        
        citation_contributors = checker.parse_citation_cff()
        codemeta_contributors = checker.parse_codemeta_json()
        
        assert len(citation_contributors) == 0
        assert len(codemeta_contributors) == 0
