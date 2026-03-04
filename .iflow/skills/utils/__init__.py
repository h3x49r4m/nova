#!/usr/bin/env python3
"""
Shared utilities for iFlow CLI skills.
"""

from .git_command import (
    run_git_command,
    validate_git_repo,
    get_current_branch,
    get_repo_root,
    validate_branch_name,
    validate_file_path
)

from .file_lock import (
    FileLock,
    FileLockError,
    locked_file,
    read_locked_json,
    write_locked_json
)

from .schema_validator import (
    SchemaValidator,
    SchemaValidationError,
    validate_workflow_state,
    validate_branch_state
)

from .exceptions import (
    IFlowError,
    ErrorCode,
    ValidationError,
    SecurityError,
    FileError,
    GitError,
    GitCommandTimeout
)

from .constants import (
    Timeouts,
    CoverageThresholds,
    CommitTypes,
    SecretPatterns,
    DEFAULT_PROTECTED_BRANCHES,
    DEFAULT_COVERAGE_THRESHOLDS
)

from .structured_logger import (
    StructuredLogger,
    LogFormat
)

__all__ = [
    'GitError',
    'GitCommandTimeout',
    'run_git_command',
    'validate_git_repo',
    'get_current_branch',
    'get_repo_root',
    'validate_branch_name',
    'validate_file_path',
    'FileLock',
    'FileLockError',
    'locked_file',
    'read_locked_json',
    'write_locked_json',
    'SchemaValidator',
    'SchemaValidationError',
    'validate_workflow_state',
    'validate_branch_state',
    'IFlowError',
    'ErrorCode',
    'ValidationError',
    'SecurityError',
    'FileError',
    'Timeouts',
    'CoverageThresholds',
    'CommitTypes',
    'SecretPatterns',
    'DEFAULT_PROTECTED_BRANCHES',
    'DEFAULT_COVERAGE_THRESHOLDS',
    'StructuredLogger',
    'LogFormat'
]