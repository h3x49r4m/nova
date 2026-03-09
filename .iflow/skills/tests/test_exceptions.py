#!/usr/bin/env python3
"""
Test suite for exceptions.py
Tests exception hierarchy and error handling utilities.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.exceptions import (
    IFlowError,
    ErrorCode,
    ErrorCategory,
    GitError,
    GitCommandTimeout,
    FileError,
    ConfigError,
    SkillError,
    WorkflowError,
    ValidationError,
    SecurityError,
    BackupError,
    VersionError,
    wrap_error,
    is_retryable
)


class TestErrorCode(unittest.TestCase):
    """Test cases for ErrorCode enum."""

    def test_success_code(self):
        """Test SUCCESS error code."""
        self.assertEqual(ErrorCode.SUCCESS.value, 0)

    def test_error_code_values(self):
        """Test error code values."""
        self.assertEqual(ErrorCode.UNKNOWN_ERROR.value, 1)
        self.assertEqual(ErrorCode.FILE_NOT_FOUND.value, 20)
        self.assertEqual(ErrorCode.GIT_COMMAND_FAILED.value, 11)

    def test_error_code_names(self):
        """Test error code names."""
        self.assertEqual(ErrorCode.UNKNOWN_ERROR.name, "UNKNOWN_ERROR")
        self.assertEqual(ErrorCode.FILE_NOT_FOUND.name, "FILE_NOT_FOUND")


class TestErrorCategory(unittest.TestCase):
    """Test cases for ErrorCategory enum."""

    def test_category_values(self):
        """Test category values."""
        self.assertEqual(ErrorCategory.TRANSIENT.value, "transient")
        self.assertEqual(ErrorCategory.PERMANENT.value, "permanent")
        self.assertEqual(ErrorCategory.CONFIGURATION.value, "configuration")


class TestIFlowError(unittest.TestCase):
    """Test cases for IFlowError base class."""

    def test_basic_error_creation(self):
        """Test basic error creation."""
        error = IFlowError("Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.code, ErrorCode.UNKNOWN_ERROR)
        self.assertEqual(error.category, ErrorCategory.PERMANENT)

    def test_error_with_code(self):
        """Test error creation with error code."""
        error = IFlowError("File not found", ErrorCode.FILE_NOT_FOUND)
        self.assertEqual(error.code, ErrorCode.FILE_NOT_FOUND)

    def test_error_with_category(self):
        """Test error creation with category."""
        error = IFlowError("Network timeout", ErrorCode.TIMEOUT, ErrorCategory.TRANSIENT)
        self.assertEqual(error.category, ErrorCategory.TRANSIENT)

    def test_error_with_details(self):
        """Test error creation with details."""
        error = IFlowError("Invalid input", details={"field": "email", "value": "invalid"})
        self.assertEqual(error.details["field"], "email")
        self.assertEqual(error.details["value"], "invalid")

    def test_error_with_cause(self):
        """Test error creation with cause."""
        original_error = ValueError("Original error")
        error = IFlowError("Wrapper error", cause=original_error)
        self.assertEqual(error.cause, original_error)

    def test_to_dict(self):
        """Test error serialization to dict."""
        error = IFlowError("Test error", ErrorCode.FILE_NOT_FOUND, details={"path": "/test"})
        result = error.to_dict()
        self.assertEqual(result["message"], "Test error")
        self.assertEqual(result["code"], "FILE_NOT_FOUND")
        self.assertEqual(result["code_value"], 20)
        self.assertEqual(result["category"], "permanent")
        self.assertEqual(result["details"]["path"], "/test")

    def test_str_representation(self):
        """Test string representation."""
        error = IFlowError("Test error", ErrorCode.FILE_NOT_FOUND)
        error_str = str(error)
        self.assertIn("FILE_NOT_FOUND", error_str)
        self.assertIn("Test error", error_str)


class TestSpecificErrors(unittest.TestCase):
    """Test cases for specific error types."""

    def test_git_error(self):
        """Test GitError creation."""
        error = GitError("Git command failed", ErrorCode.GIT_COMMAND_FAILED)
        self.assertEqual(error.category, ErrorCategory.TRANSIENT)
        self.assertEqual(error.code, ErrorCode.GIT_COMMAND_FAILED)

    def test_git_command_timeout(self):
        """Test GitCommandTimeout creation."""
        error = GitCommandTimeout("Git command timeout", command=["git", "push"], timeout=120)
        self.assertEqual(error.code, ErrorCode.TIMEOUT)
        self.assertEqual(error.details["command"], "git push")
        self.assertEqual(error.details["timeout"], 120)

    def test_file_error(self):
        """Test FileError creation."""
        error = FileError("File not found", ErrorCode.FILE_NOT_FOUND)
        self.assertEqual(error.category, ErrorCategory.PERMANENT)

    def test_config_error(self):
        """Test ConfigError creation."""
        error = ConfigError("Invalid config", ErrorCode.CONFIG_INVALID)
        self.assertEqual(error.category, ErrorCategory.CONFIGURATION)

    def test_skill_error(self):
        """Test SkillError creation."""
        error = SkillError("Skill not found", ErrorCode.SKILL_NOT_FOUND)
        self.assertEqual(error.category, ErrorCategory.DEPENDENCY)

    def test_workflow_error(self):
        """Test WorkflowError creation."""
        error = WorkflowError("Workflow failed", ErrorCode.WORKFLOW_NOT_INITIALIZED)
        self.assertEqual(error.category, ErrorCategory.PERMANENT)

    def test_validation_error(self):
        """Test ValidationError creation."""
        error = ValidationError("Invalid input", ErrorCode.VALIDATION_ERROR)
        self.assertEqual(error.category, ErrorCategory.USER_ERROR)

    def test_security_error(self):
        """Test SecurityError creation."""
        error = SecurityError("Secret detected", ErrorCode.SECRET_DETECTED)
        self.assertEqual(error.category, ErrorCategory.PERMANENT)

    def test_backup_error(self):
        """Test BackupError creation."""
        error = BackupError("Backup failed", ErrorCode.BACKUP_FAILED)
        self.assertEqual(error.category, ErrorCategory.TRANSIENT)

    def test_version_error(self):
        """Test VersionError creation."""
        error = VersionError("Version mismatch", ErrorCode.VERSION_MISMATCH)
        self.assertEqual(error.category, ErrorCategory.DEPENDENCY)


class TestErrorUtilities(unittest.TestCase):
    """Test cases for error utility functions."""

    def test_wrap_error_with_exception(self):
        """Test wrapping an exception."""
        original_error = ValueError("Original error")
        wrapped = wrap_error(original_error, "Wrapped error")
        self.assertIsInstance(wrapped, IFlowError)
        self.assertEqual(wrapped.message, "Wrapped error")
        self.assertEqual(wrapped.cause, original_error)

    def test_wrap_error_with_iflow_error(self):
        """Test wrapping an IFlowError (should return as-is)."""
        original_error = IFlowError("Original error")
        wrapped = wrap_error(original_error, "Wrapped error")
        self.assertEqual(wrapped, original_error)

    def test_wrap_error_with_code(self):
        """Test wrapping with error code."""
        original_error = ValueError("Original error")
        wrapped = wrap_error(original_error, "Wrapped error", code=ErrorCode.FILE_NOT_FOUND)
        self.assertEqual(wrapped.code, ErrorCode.FILE_NOT_FOUND)

    def test_wrap_error_with_category(self):
        """Test wrapping with error category."""
        original_error = ValueError("Original error")
        wrapped = wrap_error(original_error, "Wrapped error", category=ErrorCategory.TRANSIENT)
        self.assertEqual(wrapped.category, ErrorCategory.TRANSIENT)

    def test_is_retryable_with_transient_error(self):
        """Test is_retryable with transient error."""
        error = GitError("Network timeout", ErrorCode.TIMEOUT, ErrorCategory.TRANSIENT)
        self.assertTrue(is_retryable(error))

    def test_is_retryable_with_permanent_error(self):
        """Test is_retryable with permanent error."""
        error = FileError("File not found", ErrorCode.FILE_NOT_FOUND, ErrorCategory.PERMANENT)
        self.assertFalse(is_retryable(error))

    def test_is_retryable_with_regular_exception(self):
        """Test is_retryable with regular exception (not IFlowError)."""
        error = ValueError("Regular exception")
        self.assertFalse(is_retryable(error))


if __name__ == '__main__':
    unittest.main()