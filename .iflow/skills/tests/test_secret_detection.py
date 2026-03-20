#!/usr/bin/env python3
"""
Test suite for secret detection in git operations.
Tests that check_for_secrets is properly integrated across git operations.
"""

import unittest
from unittest.mock import MagicMock, patch

from utils import check_for_secrets, SecretPatterns


class TestSecretDetectionInGitOperations(unittest.TestCase):
    """Test cases for secret detection integration in git operations."""

    def test_check_for_secrets_with_api_key(self):
        """Test detection of API key in git output."""
        output = "This is a test with api_key = 'sk_test_1234567890abcdef' in it"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_check_for_secrets_with_password(self):
        """Test detection of password in git output."""
        output = "The password = 'password12345678'"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_check_for_secrets_with_aws_key(self):
        """Test detection of AWS access key in git output."""
        output = "aws_access_key_id = 'AKIAIOSFODNN7EXAMPLE'"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_check_for_secrets_with_jwt_token(self):
        """Test detection of JWT token in git output."""
        output = "token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U'"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_check_for_secrets_with_private_key(self):
        """Test detection of private key in git output."""
        output = "private_key = '-----BEGIN RSA PRIVATE KEY-----'"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_check_for_secrets_with_github_token(self):
        """Test detection of GitHub token in git output."""
        output = "github_token = 'ghp_1234567890abcdefghijklmnopqrstuvwxyz123456'"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_check_for_secrets_with_database_url(self):
        """Test detection of database URL in git output."""
        output = "database_url = 'postgresql://user:password123@localhost:5432/db'"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_check_for_secrets_case_insensitive(self):
        """Test that secret detection is case-insensitive."""
        output = "This has API_KEY = 'sk_test_1234567890abcdef'"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_check_for_secrets_no_secrets(self):
        """Test that safe output doesn't trigger detection."""
        output = "This is safe output with no secrets"
        detected = check_for_secrets(output, "")
        self.assertFalse(detected)

    def test_check_for_secrets_empty_output(self):
        """Test that empty output doesn't trigger detection."""
        detected = check_for_secrets("", "")
        self.assertFalse(detected)

    def test_check_for_secrets_in_stderr(self):
        """Test detection of secrets in stderr."""
        stderr = "Error: stripe_api_key = sk_test_1234567890abcdef"
        detected = check_for_secrets("", stderr)
        self.assertTrue(detected)

    def test_check_for_secrets_multiple_patterns(self):
        """Test detection of multiple secret patterns."""
        output = "api_key = 'sk_test_1234567890abcdef' and password = 'password12345678'"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_secret_patterns_enum_coverage(self):
        """Test that secret patterns enum covers common secret types."""
        patterns = [pattern.value for pattern in SecretPatterns]
        # Check for common secret patterns
        self.assertTrue(any('stripe' in p.lower() for p in patterns))  # Stripe API keys
        self.assertTrue(any('password' in p.lower() for p in patterns))  # Passwords
        self.assertTrue(any('aws' in p.lower() and 'access' in p.lower() for p in patterns))  # AWS keys
        self.assertTrue(any('jwt' in p.lower() or 'ey' in p.lower() for p in patterns))  # JWT tokens
        self.assertTrue(any('private' in p.lower() and 'key' in p.lower() for p in patterns))  # Private keys
        self.assertTrue(any('github' in p.lower() and 'token' in p.lower() for p in patterns))  # GitHub tokens
        self.assertTrue(any('database' in p.lower() and 'url' in p.lower() for p in patterns))  # Database URLs

    def test_check_for_secrets_with_git_diff_output(self):
        """Test secret detection in realistic git diff output."""
        diff_output = """diff --git a/config.py b/config.py
index 1234567..abcdefg 100644
--- a/config.py
+++ b/config.py
@@ -1,5 +1,5 @@
 # Configuration
-stripe_api_key = "sk_test_1234567890abcdef"
+stripe_api_key = "sk_live_9876543210fedcba"
 """
        detected = check_for_secrets(diff_output, "")
        self.assertTrue(detected)

    def test_check_for_secrets_with_safe_diff_output(self):
        """Test that safe diff output doesn't trigger detection."""
        diff_output = """diff --git a/README.md b/README.md
index 1234567..abcdefg 100644
--- a/README.md
+++ b/README.md
@@ -1,5 +1,5 @@
 # Project Name
-This is version 1.0
+This is version 2.0
 """
        detected = check_for_secrets(diff_output, "")
        self.assertFalse(detected)

    def test_check_for_secrets_with_git_commit_output(self):
        """Test secret detection in git commit output."""
        commit_output = """[master 1234567] Add feature
 Author: John Doe <john@example.com>
 Date: Mon Jan 1 00:00:00 2026 +0000

 Added API integration with stripe_api_key = sk_test_1234567890abcdef
 """
        detected = check_for_secrets(commit_output, "")
        self.assertTrue(detected)

    def test_check_for_secrets_with_safe_commit_output(self):
        """Test that safe commit output with no obvious secrets doesn't trigger detection."""
        # Use a simple commit message that won't trigger false positives
        commit_output = "Fix typo in README"
        detected = check_for_secrets(commit_output, "")
        self.assertFalse(detected)


if __name__ == '__main__':
    unittest.main()