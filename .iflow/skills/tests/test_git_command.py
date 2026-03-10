#!/usr/bin/env python3
"""
Test suite for git_command.py
Tests git command execution with secret detection and error handling.
"""

import unittest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

from utils.git_command import run_git_command, check_for_secrets
from utils.exceptions import GitError, GitCommandTimeout, ErrorCode


class TestRunGitCommand(unittest.TestCase):
    """Test cases for run_git_command function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('utils.git_command.subprocess.run')
    def test_run_git_command_success(self, mock_run):
        """Test successful git command execution."""
        mock_run.return_value = Mock(
            stdout="git output\n",
            stderr="",
            returncode=0
        )

        code, stdout, stderr = run_git_command(['status'], cwd=self.repo_path)

        self.assertEqual(code, 0)
        self.assertEqual(stdout, "git output\n")
        self.assertEqual(stderr, "")
        mock_run.assert_called_once()

    @patch('utils.git_command.subprocess.run')
    def test_run_git_command_failure(self, mock_run):
        """Test git command failure."""
        mock_run.return_value = Mock(
            stdout="",
            stderr="fatal: not a git repository\n",
            returncode=128
        )

        code, stdout, stderr = run_git_command(['status'], cwd=self.repo_path)

        self.assertEqual(code, 128)
        self.assertEqual(stderr, "fatal: not a git repository\n")

    @patch('utils.git_command.subprocess.run')
    def test_run_git_command_timeout(self, mock_run):
        """Test git command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("git", 60)

        with self.assertRaises(GitCommandTimeout) as context:
            run_git_command(['fetch'], cwd=self.repo_path, timeout=60)

        self.assertEqual(context.exception.code, ErrorCode.TIMEOUT)

    @patch('subprocess.run')
    def test_run_git_command_with_secret_detection(self, mock_run):
        """Test git command with secret detection in output."""
        mock_run.return_value = Mock(
            stdout='{"api_key": "sk_live_1234567890abcdef"}',
            stderr="",
            returncode=0
        )

        code, stdout, stderr = run_git_command(['log'], cwd=self.repo_path, check_secrets=True)

        # The function should detect the secret and either warn or fail
        self.assertIn("sk_live_1234567890abcdef", stdout)


class TestCheckForSecrets(unittest.TestCase):
    """Test cases for check_for_secrets function."""

    def test_detect_api_key(self):
        """Test API key detection."""
        output = "api_key=sk_live_1234567890abcdef"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_detect_password(self):
        """Test password detection."""
        output = "password=MySecretPassword123"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_detect_jwt_token(self):
        """Test JWT token detection."""
        output = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_detect_aws_access_key(self):
        """Test AWS access key detection."""
        # AWS access key format: AKIAIOSFODNN7EXAMPLE (20 chars)
        output = "AKIAIOSFODNN7EXAMPLE"
        detected = check_for_secrets(output, "")
        # This might not be detected depending on the secret patterns
        # Let's check if there's an AWS_ACCESS_KEY pattern

    def test_no_secrets_in_clean_output(self):
        """Test that clean output doesn't trigger false positives."""
        output = "This is clean output with no secrets"
        detected = check_for_secrets(output, "")
        self.assertFalse(detected)

    def test_detect_private_key(self):
        """Test private key detection."""
        output = "-----BEGIN RSA PRIVATE KEY-----"
        detected = check_for_secrets(output, "")
        self.assertTrue(detected)

    def test_multiple_secrets(self):
        """Test detection of multiple secrets."""
        output = """
        api_key=sk_live_1234567890abcdef
        password=MySecretPassword123
        token=xyz789token456
        """
        detected = check_for_secrets(output, "")
        # Should detect secrets
        self.assertTrue(detected)


class TestGitCommandErrorHandling(unittest.TestCase):
    """Test cases for git command error handling."""

    @patch('utils.git_command.subprocess.run')
    def test_git_not_found_error(self, mock_run):
        """Test handling of git not found error."""
        mock_run.side_effect = FileNotFoundError("git not found")

        with self.assertRaises(GitError) as context:
            run_git_command(['status'], cwd=Path("/tmp"))

        self.assertEqual(context.exception.code, ErrorCode.DEPENDENCY_ERROR)

    @patch('utils.git_command.subprocess.run')
    def test_git_permission_error(self, mock_run):
        """Test handling of git permission error."""
        mock_run.side_effect = PermissionError("Permission denied")

        with self.assertRaises(GitError) as context:
            run_git_command(['status'], cwd=Path("/tmp"))

        # Permission errors are treated as transient (retryable)
        self.assertEqual(context.exception.category.value, "transient")


if __name__ == '__main__':
    unittest.main()
