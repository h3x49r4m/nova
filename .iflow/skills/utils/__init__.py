#!/usr/bin/env python3
"""
Shared utilities for iFlow CLI skills.
"""

from .checkpoint_manager import CheckpointManager
from .config_manager import ConfigManager, SkillType
from .constants import (
    DEFAULT_COVERAGE_THRESHOLDS,
    DEFAULT_PROTECTED_BRANCHES,
    BranchStatus,
    CommitTypes,
    CoverageThresholds,
    PhaseStatus,
    RegexPatterns,
    SecretPatterns,
    Timeouts,
    WorkflowStatus,
)
from .deadlock_detector import DeadlockDetector, validate_git_flow_dependencies
from .exceptions import (
    ErrorCategory,
    ErrorCode,
    FileError,
    GitCommandTimeout,
    GitError,
    IFlowError,
    SecurityError,
    ValidationError,
)
from .file_lock import (
    FileLock,
    FileLockError,
    locked_file,
    read_locked_json,
    write_locked_json,
)
from .git_command import (
    get_current_branch,
    get_repo_root,
    run_git_command,
    validate_branch_name,
    validate_file_path,
    validate_git_repo,
)
from .input_sanitizer import InputSanitizer
from .prerequisite_checker import PrerequisiteChecker, validate_workflow_prerequisites
from .schema_validator import (
    SchemaValidationError,
    SchemaValidator,
    validate_branch_state,
    validate_json_schema,
    validate_workflow_state,
)
from .structured_logger import LogFormat, LogLevel, StructuredLogger

__all__ = [
    'DEFAULT_COVERAGE_THRESHOLDS',
    'DEFAULT_PROTECTED_BRANCHES',
    'BranchStatus',
    'CheckpointManager',
    'CommitTypes',
    'ConfigManager',
    'CoverageThresholds',
    'DeadlockDetector',
    'ErrorCategory',
    'ErrorCode',
    'FileError',
    'FileLock',
    'FileLockError',
    'GitCommandTimeout',
    'GitError',
    'IFlowError',
    'InputSanitizer',
    'LogFormat',
    'LogLevel',
    'PhaseStatus',
    'PrerequisiteChecker',
    'RegexPatterns',
    'SchemaValidationError',
    'SchemaValidator',
    'SecretPatterns',
    'SecurityError',
    'SkillType',
    'StructuredLogger',
    'Timeouts',
    'ValidationError',
    'WorkflowStatus',
    'get_current_branch',
    'get_repo_root',
    'locked_file',
    'read_locked_json',
    'run_git_command',
    'validate_branch_name',
    'validate_branch_state',
    'validate_file_path',
    'validate_git_flow_dependencies',
    'validate_git_repo',
    'validate_json_schema',
    'validate_workflow_prerequisites',
    'validate_workflow_state',
    'write_locked_json'
]
