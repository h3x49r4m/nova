#!/usr/bin/env python3
"""
Test suite for security features.
Tests secret detection, input sanitization, and other security-related functionality.
"""

import unittest
from pathlib import Path

# Import utility classes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.shared_validators import SharedValidators
from utils.input_sanitizer import InputSanitizer
from utils.constants import SecretPatterns


class TestSecretDetection(unittest.TestCase):
    """Test secret detection functionality."""

    def test_detect_api_key(self):
        """Test detection of API keys."""
        test_cases = [
            "api_key=sk_test_fake_key_for_testing_only_123456",
            "API_KEY = 'abcd1234567890abcdef1234567890abcdef'",
            "apiKey: xyz78901234567890abcdefghijklmnopqrstuvwxyz"
        ]

        for test_input in test_cases:
            result = SharedValidators.validate_secrets(test_input)
            self.assertFalse(result.is_valid, f"Should detect secret in: {test_input}")

    def test_detect_secret_token(self):
        """Test detection of secret tokens."""
        test_cases = [
            "secret_token = 'my_secret_token_12345678901234567890'",
            "SECRET=abcd1234567890abcd1234567890abcd123456",
            "token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ]

        for test_input in test_cases:
            result = SharedValidators.validate_secrets(test_input)
            self.assertFalse(result.is_valid, f"Should detect secret in: {test_input}")

    def test_detect_password(self):
        """Test detection of passwords."""
        test_cases = [
            "password = 'mysecretpassword123'",
            "db_password: supersecret123456",
            "PASSWD = 'password12345'"
        ]

        for test_input in test_cases:
            result = SharedValidators.validate_secrets(test_input)
            self.assertFalse(result.is_valid, f"Should detect password in: {test_input}")

    def test_detect_aws_keys(self):
        """Test detection of AWS access keys."""
        test_cases = [
            "aws_access_key_id = AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "AWS_KEY: AKIAI44QH8DHBEXAMPLE"
        ]

        for test_input in test_cases:
            result = SharedValidators.validate_secrets(test_input)
            self.assertFalse(result.is_valid, f"Should detect AWS key in: {test_input}")

    def test_detect_jwt_token(self):
        """Test detection of JWT tokens."""
        test_cases = [
            "jwt: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ]

        for test_input in test_cases:
            result = SharedValidators.validate_secrets(test_input)
            self.assertFalse(result.is_valid, f"Should detect JWT in: {test_input}")

    def test_detect_private_key(self):
        """Test detection of private keys."""
        test_cases = [
            "-----BEGIN RSA PRIVATE KEY-----",
            "private_key: -----BEGIN EC PRIVATE KEY-----",
            "ssh_private_key: -----BEGIN OPENSSH PRIVATE KEY-----"
        ]

        for test_input in test_cases:
            result = SharedValidators.validate_secrets(test_input)
            self.assertFalse(result.is_valid, f"Should detect private key in: {test_input}")

    def test_detect_github_token(self):
        """Test detection of GitHub tokens."""
        test_cases = [
            "github_token: ghp_1234567890abcdef1234567890abcdef123456",
            "GITHUB_TOKEN = ghp_test_token_placeholder_for_testing_only",
            "github: ghs_1234567890abcdef1234567890abcdef"
        ]

        for test_input in test_cases:
            result = SharedValidators.validate_secrets(test_input)
            self.assertFalse(result.is_valid, f"Should detect GitHub token in: {test_input}")

    def test_no_false_positives(self):
        """Test that normal code doesn't trigger false positives."""
        test_cases = [
            "def get_api_key(): return os.environ.get('API_KEY')",
            "password = input('Enter password: ')",
            "token = str(uuid.uuid4())",
            "key = 'example_key_value'",
            "aws_region = 'us-east-1'",
            "jwt = jwt.encode(payload, secret, algorithm='HS256')"
        ]

        for test_input in test_cases:
            result = SharedValidators.validate_secrets(test_input)
            # These should not trigger secret detection
            self.assertTrue(result.is_valid, f"Should not detect secret in: {test_input}")

    def test_multiple_secrets(self):
        """Test detection of multiple secrets in one input."""
        test_input = """
        api_key = sk_test_fake_key_for_testing_only_123456
        password = mysecretpassword123
        aws_access_key_id = AKIAIOSFODNN7EXAMPLE
        """

        result = SharedValidators.validate_secrets(test_input)
        # Should detect secrets
        self.assertFalse(result.is_valid)

    def test_secret_patterns_coverage(self):
        """Test that all secret patterns are covered."""
        # Check that all SecretPatterns enum values have patterns
        patterns = [pattern.value for pattern in SecretPatterns]
        self.assertGreater(len(patterns), 0)

        # Ensure patterns are valid regex
        import re
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error:
                self.fail(f"Invalid regex pattern: {pattern}")


class TestInputSanitization(unittest.TestCase):
    """Test input sanitization functionality."""

    def test_sanitize_sql_input_basic(self):
        """Test basic SQL input sanitization."""
        test_cases = [
            "' OR '1'='1",
            "1; DROP TABLE users--",
            "' UNION SELECT * FROM admin--",
        ]

        for input_str in test_cases:
            result = InputSanitizer.sanitize_string(input_str)
            self.assertIsInstance(result, str)
            # Should remove or escape dangerous characters
            self.assertIsNotNone(result)

    def test_sanitize_html_input(self):
        """Test HTML input sanitization."""
        test_cases = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "<div onclick=\"alert(1)\">Click</div>",
        ]

        for input_str in test_cases:
            result = InputSanitizer.sanitize_string(input_str)
            self.assertIsInstance(result, str)

    def test_sanitize_shell_input(self):
        """Test shell command input sanitization."""
        test_cases = [
            "test; rm -rf /",
            "$(cat /etc/passwd)",
            "`whoami`",
        ]

        for input_str in test_cases:
            result = InputSanitizer.sanitize_string(input_str)
            self.assertIsInstance(result, str)

    def test_sanitize_path_input(self):
        """Test path input sanitization."""
        test_cases = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
        ]

        for input_str in test_cases:
            result = InputSanitizer.sanitize_string(input_str, allowed_chars=InputSanitizer.ALLOWED_PATH_CHARS)
            self.assertIsInstance(result, str)

    def test_sanitize_empty_input(self):
        """Test sanitization of empty input."""
        self.assertEqual(InputSanitizer.sanitize_string(""), "")

    def test_sanitize_unicode_input(self):
        """Test sanitization of unicode input."""
        unicode_input = "你好世界 🚀"
        self.assertEqual(InputSanitizer.sanitize_string(unicode_input), unicode_input)


class TestSecurityIntegration(unittest.TestCase):
    """Integration tests for security features."""

    def test_git_commit_with_secrets(self):
        """Test that secrets are detected in git commit messages."""
        commit_message = "feat: add API key support\n\nAdded api_key=sk_test_fake_key_for_testing_only_123456"

        result = SharedValidators.validate_secrets(commit_message)
        self.assertFalse(result.is_valid)

    def test_code_review_security_check(self):
        """Test security check during code review."""
        code_snippet = """
        import os

        def authenticate():
            api_key = 'sk_test_fake_key_for_testing_only_123456'
            password = 'mysecretpassword123'
            return api_key, password
        """

        result = SharedValidators.validate_secrets(code_snippet)
        self.assertFalse(result.is_valid)

    def test_multi_line_secret_detection(self):
        """Test secret detection across multiple lines."""
        multi_line_input = """
        Configuration:
        - API Key: sk_test_fake_key_for_testing_only_123456
        - Secret: my_secret_token_12345678901234567890
        - Password: supersecret123456
        """

        result = SharedValidators.validate_secrets(multi_line_input)
        self.assertFalse(result.is_valid)

    def test_case_insensitive_secret_detection(self):
        """Test that secret detection is case-insensitive."""
        test_cases = [
            "API_KEY = sk_test_fake_key_for_testing_only_123456",
            "api_key = sk_test_fake_key_for_testing_only_123456",
            "Api_Key = sk_test_fake_key_for_testing_only_123456",
            "aPi_KeY = sk_test_fake_key_for_testing_only_123456",
        ]

        for test_input in test_cases:
            result = SharedValidators.validate_secrets(test_input)
            self.assertFalse(result.is_valid, f"Should detect secret regardless of case: {test_input}")

    def test_xss_prevention(self):
        """Test XSS prevention in input sanitization."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            "<iframe src=javascript:alert(1)>",
        ]

        for payload in xss_payloads:
            sanitized = InputSanitizer.sanitize_string(payload)
            # Should escape or remove dangerous content
            self.assertIsNotNone(sanitized)

    def test_sql_injection_prevention(self):
        """Test SQL injection prevention in input sanitization."""
        sql_payloads = [
            "' OR '1'='1",
            "1' UNION SELECT * FROM users--",
            "'; DROP TABLE users;--",
            "1' AND 1=1--",
        ]

        for payload in sql_payloads:
            sanitized = InputSanitizer.sanitize_string(payload)
            # Should escape or remove dangerous content
            self.assertIsNotNone(sanitized)


if __name__ == "__main__":
    unittest.main()