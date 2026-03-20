#!/usr/bin/env python3
"""
Test suite for exceptions.py
Tests exception hierarchy and error handling utilities.
"""

import unittest

from utils.exceptions import (
    BackupError,
    ConfigError,
    ErrorCategory,
    ErrorCode,
    FileError,
    GitCommandTimeout,
    GitError,
    IFlowError,
    SchemaValidationError,
    SecurityError,
    SkillError,
    ValidationError,
    VersionError,
    WorkflowError,
    is_retryable,
    wrap_error,
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


class TestSchemaValidationError(unittest.TestCase):
    """Test cases for SchemaValidationError class."""

    def test_basic_error_creation(self):
        """Test basic SchemaValidationError creation."""
        error = SchemaValidationError("Schema validation failed")
        self.assertEqual(error.message, "Schema validation failed")
        self.assertEqual(error.code, ErrorCode.SCHEMA_VALIDATION_FAILED)
        self.assertEqual(error.category, ErrorCategory.USER_ERROR)
        self.assertEqual(error.errors, [])
        self.assertEqual(error.path, "")
        self.assertIsNone(error.error_type)

    def test_error_with_errors_parameter(self):
        """Test SchemaValidationError with errors parameter (schema_validator style)."""
        errors = ["Missing required field: name", "Invalid type for age"]
        error = SchemaValidationError("Validation failed", errors=errors)
        self.assertEqual(error.errors, errors)
        self.assertIn("errors", error.details)
        self.assertEqual(error.details["errors"], errors)

    def test_error_with_path_parameter(self):
        """Test SchemaValidationError with path parameter (json_schema_validator style)."""
        error = SchemaValidationError("Type mismatch", path="user.age")
        self.assertEqual(error.path, "user.age")
        self.assertIn("path", error.details)
        self.assertEqual(error.details["path"], "user.age")

    def test_error_with_error_type_parameter(self):
        """Test SchemaValidationError with error_type parameter (json_schema_validator style)."""
        error = SchemaValidationError("Type mismatch", error_type="TYPE_MISMATCH")
        self.assertEqual(error.error_type, "TYPE_MISMATCH")
        self.assertIn("error_type", error.details)
        self.assertEqual(error.details["error_type"], "TYPE_MISMATCH")

    def test_error_with_all_parameters(self):
        """Test SchemaValidationError with all parameters."""
        errors = ["Invalid value"]
        error = SchemaValidationError(
            "Multiple validation errors",
            errors=errors,
            path="user.email",
            error_type="FORMAT_INVALID"
        )
        self.assertEqual(error.errors, errors)
        self.assertEqual(error.path, "user.email")
        self.assertEqual(error.error_type, "FORMAT_INVALID")
        self.assertIn("errors", error.details)
        self.assertIn("path", error.details)
        self.assertIn("error_type", error.details)

    def test_inheritance_from_validation_error(self):
        """Test that SchemaValidationError inherits from ValidationError."""
        error = SchemaValidationError("Test error")
        self.assertIsInstance(error, ValidationError)

    def test_inheritance_from_iflow_error(self):
        """Test that SchemaValidationError inherits from IFlowError."""
        error = SchemaValidationError("Test error")
        self.assertIsInstance(error, IFlowError)

    def test_error_code_is_schema_validation_failed(self):
        """Test that error code is SCHEMA_VALIDATION_FAILED."""
        error = SchemaValidationError("Test error")
        self.assertEqual(error.code, ErrorCode.SCHEMA_VALIDATION_FAILED)
        self.assertEqual(error.code.value, 34)

    def test_to_dict_includes_errors(self):
        """Test that to_dict includes errors in details."""
        errors = ["Error 1", "Error 2"]
        error = SchemaValidationError("Test", errors=errors)
        result = error.to_dict()
        self.assertIn("details", result)
        self.assertIn("errors", result["details"])
        self.assertEqual(result["details"]["errors"], errors)

    def test_to_dict_includes_path(self):
        """Test that to_dict includes path in details."""
        error = SchemaValidationError("Test", path="field.path")
        result = error.to_dict()
        self.assertIn("details", result)
        self.assertIn("path", result["details"])
        self.assertEqual(result["details"]["path"], "field.path")

    def test_to_dict_includes_error_type(self):
        """Test that to_dict includes error_type in details."""
        error = SchemaValidationError("Test", error_type="ENUM_MISMATCH")
        result = error.to_dict()
        self.assertIn("details", result)
        self.assertIn("error_type", result["details"])
        self.assertEqual(result["details"]["error_type"], "ENUM_MISMATCH")

    def test_str_representation_with_errors(self):
        """Test string representation with errors."""
        error = SchemaValidationError("Test", errors=["Error 1"])
        error_str = str(error)
        self.assertIn("SCHEMA_VALIDATION_FAILED", error_str)
        self.assertIn("Test", error_str)

    def test_empty_errors_list(self):
        """Test SchemaValidationError with empty errors list."""
        error = SchemaValidationError("Test", errors=[])
        self.assertEqual(error.errors, [])

    def test_none_error_type(self):
        """Test SchemaValidationError with None error_type."""
        error = SchemaValidationError("Test", error_type=None)
        self.assertIsNone(error.error_type)

    def test_empty_path_string(self):
        """Test SchemaValidationError with empty path string."""
        error = SchemaValidationError("Test", path="")
        self.assertEqual(error.path, "")

    def test_details_not_included_when_empty(self):
        """Test that details are not included when all parameters are empty."""
        error = SchemaValidationError("Test")
        result = error.to_dict()
        # Details should not be in result when all optional parameters are empty
        self.assertNotIn("details", result)

    def test_backwards_compatibility_schema_validator_style(self):
        """Test backwards compatibility with schema_validator usage pattern."""
        # This simulates how schema_validator.py was using the exception
        errors = ["Missing required field: name"]
        error = SchemaValidationError("Schema validation failed", errors=errors)
        self.assertEqual(error.message, "Schema validation failed")
        self.assertEqual(error.errors, errors)

    def test_backwards_compatibility_json_schema_validator_style(self):
        """Test backwards compatibility with json_schema_validator usage pattern."""
        # This simulates how json_schema_validator.py was using the exception
        error = SchemaValidationError(
            "Schema validation failed",
            path="user.name",
            error_type="TYPE_MISMATCH"
        )
        self.assertEqual(error.message, "Schema validation failed")
        self.assertEqual(error.path, "user.name")
        self.assertEqual(error.error_type, "TYPE_MISMATCH")


if __name__ == '__main__':
    unittest.main()
