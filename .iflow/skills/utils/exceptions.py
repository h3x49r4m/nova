#!/usr/bin/env python3
"""
Common Exception Classes
Standardized exception hierarchy for the iFlow CLI skills system.
"""

from typing import Optional, Dict, Any, List
from enum import Enum


class ErrorCategory(Enum):
    """Categories of errors for classification and handling."""
    TRANSIENT = "transient"  # Retryable errors (network, timeouts)
    PERMANENT = "permanent"  # Non-retryable errors (validation, auth)
    CONFIGURATION = "configuration"  # Config/setup errors
    DEPENDENCY = "dependency"  # Missing/failed dependencies
    USER_ERROR = "user_error"  # User input errors
    SYSTEM_ERROR = "system_error"  # System-level errors


class ErrorCode(Enum):
    """Standardized error codes across the codebase."""
    # Success
    SUCCESS = 0

    # General errors (1-10)
    UNKNOWN_ERROR = 1
    INVALID_INPUT = 2
    INVALID_ARGUMENT = 2
    OPERATION_FAILED = 3
    TIMEOUT = 4
    VALIDATION_ERROR = 5

    # Git operations (10-20)
    GIT_NOT_FOUND = 10
    GIT_COMMAND_FAILED = 11
    GIT_REPOSITORY_NOT_FOUND = 12
    GIT_BRANCH_PROTECTED = 13
    GIT_MERGE_CONFLICT = 14
    GIT_REBASE_FAILED = 15

    # File operations (20-30)
    FILE_NOT_FOUND = 20
    FILE_READ_ERROR = 21
    FILE_WRITE_ERROR = 22
    INVALID_PATH = 23
    PATH_TRAVERSAL_DETECTED = 24

    # State/Configuration (30-40)
    CONFIG_NOT_FOUND = 30
    CONFIG_INVALID = 31
    STATE_CORRUPTED = 32
    STATE_VERSION_MISMATCH = 33
    SCHEMA_VALIDATION_FAILED = 34
    DEPENDENCY_ERROR = 35

    # Skill/Pipeline (40-50)
    SKILL_NOT_FOUND = 40
    SKILL_VERSION_INCOMPATIBLE = 41
    PIPELINE_NOT_FOUND = 42
    WORKFLOW_NOT_FOUND = 43
    PREREQUISITE_FAILED = 44

    # Workflow/Git-Flow (50-60)
    WORKFLOW_NOT_INITIALIZED = 50
    PHASE_ALREADY_ACTIVE = 51
    PHASE_NOT_FOUND = 52
    BRANCH_NOT_FOUND = 53
    APPROVAL_REQUIRED = 54
    DEPENDENCY_NOT_MET = 55

    # Testing (60-70)
    TEST_FAILED = 60
    TEST_TIMEOUT = 61
    COVERAGE_BELOW_THRESHOLD = 62

    # Security (70-80)
    SECRET_DETECTED = 70
    SECURITY_VIOLATION = 71
    ACCESS_DENIED = 72
    AUTHENTICATION_FAILED = 73
    AUTHORIZATION_FAILED = 74

    # Validation (80-90)
    VALIDATION_FAILED = 80
    REQUIRED_FIELD_MISSING = 81
    INVALID_VALUE = 82
    PATTERN_MISMATCH = 83

    # Backup (90-100)
    BACKUP_FAILED = 90
    BACKUP_NOT_FOUND = 91
    BACKUP_CORRUPTED = 92
    RESTORE_FAILED = 93
    LOCK_ERROR = 94
    VERSION_MISMATCH = 95


class IFlowError(Exception):
    """Base exception class for all iFlow CLI errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        category: ErrorCategory = ErrorCategory.PERMANENT,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize iFlow error.

        Args:
            message: Human-readable error message
            code: Standardized error code
            category: Error category for handling
            details: Additional error context
            cause: Original exception if wrapping
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.details: Dict[str, Any] = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        result: Dict[str, Any] = {
            "message": self.message,
            "code": self.code.name,
            "code_value": self.code.value,
            "category": self.category.value
        }
        if self.details:
            result["details"] = self.details
        if self.cause:
            result["cause"] = str(self.cause)
        return result

    def __str__(self) -> str:
        """String representation of the error."""
        base = f"[{self.code.name}] {self.message}"
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            base += f" ({details_str})"
        return base


class GitError(IFlowError):
    """Git-related errors."""

    def __init__(self, message: str, code: ErrorCode, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, code, ErrorCategory.TRANSIENT, details, cause)


class GitCommandTimeout(GitError):
    """Git command timeout errors."""

    def __init__(self, message: str, command: Optional[List[str]] = None, timeout: Optional[int] = None):
        details: Dict[str, Any] = {}
        if command:
            details['command'] = ' '.join(command)
        if timeout:
            details['timeout'] = timeout
        super().__init__(message, ErrorCode.TIMEOUT, details)


class FileError(IFlowError):
    """File operation errors."""

    def __init__(self, message: str, code: ErrorCode, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, code, ErrorCategory.PERMANENT, details, cause)


class ConfigError(IFlowError):
    """Configuration errors."""

    def __init__(self, message: str, code: ErrorCode, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, code, ErrorCategory.CONFIGURATION, details, cause)


class SkillError(IFlowError):
    """Skill-related errors."""

    def __init__(self, message: str, code: ErrorCode, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, code, ErrorCategory.DEPENDENCY, details, cause)


class WorkflowError(IFlowError):
    """Workflow-related errors."""

    def __init__(self, message: str, code: ErrorCode, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, code, ErrorCategory.PERMANENT, details, cause)


class ValidationError(IFlowError):
    """Validation errors."""

    def __init__(self, message: str, code: ErrorCode, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, code, ErrorCategory.USER_ERROR, details, cause)


class SecurityError(IFlowError):
    """Security-related errors."""

    def __init__(self, message: str, code: ErrorCode, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, code, ErrorCategory.PERMANENT, details, cause)


class BackupError(IFlowError):
    """Backup-related errors."""

    def __init__(self, message: str, code: ErrorCode, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, code, ErrorCategory.TRANSIENT, details, cause)


class VersionError(IFlowError):
    """Version-related errors."""

    def __init__(self, message: str, code: ErrorCode, details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message, code, ErrorCategory.DEPENDENCY, details, cause)


def wrap_error(
    original_error: Exception,
    message: Optional[str] = None,
    code: Optional[ErrorCode] = None,
    category: Optional[ErrorCategory] = None
) -> IFlowError:
    """
    Wrap an exception in an IFlowError.

    Args:
        original_error: The original exception to wrap
        message: Optional custom message (defaults to original message)
        code: Optional error code (defaults to UNKNOWN_ERROR)
        category: Optional error category

    Returns:
        IFlowError wrapping the original exception
    """
    if isinstance(original_error, IFlowError):
        return original_error

    error_message = message or str(original_error)
    error_code = code or ErrorCode.UNKNOWN_ERROR
    error_category = category or ErrorCategory.PERMANENT

    return IFlowError(
        message=error_message,
        code=error_code,
        category=error_category,
        cause=original_error
    )


def is_retryable(error: Exception) -> bool:
    """
    Check if an error is retryable.

    Args:
        error: Exception to check

    Returns:
        True if error should be retried
    """
    if isinstance(error, IFlowError):
        return error.category == ErrorCategory.TRANSIENT
    return False