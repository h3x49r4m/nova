#!/usr/bin/env python3
"""
Shared Validation Utilities
Provides centralized validation functions to eliminate code duplication.
"""

import re
from typing import Tuple, Optional, List, Any
from pathlib import Path
from enum import Enum

from .constants import (
    ValidationPatterns,
    CommitTypes,
    SecretPatterns
)


class ValidationResult:
    """Container for validation results."""

    def __init__(
        self,
        is_valid: bool,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        self.is_valid = is_valid
        self.error_message = error_message
        self.error_code = error_code
        self.metadata = metadata or {}

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "metadata": self.metadata
        }


class SharedValidators:
    """Shared validation functions used across the codebase."""

    @staticmethod
    def validate_branch_name(branch_name: str) -> ValidationResult:
        """
        Validate a git branch name according to git naming rules.

        Args:
            branch_name: The branch name to validate

        Returns:
            ValidationResult with validation outcome
        """
        if not branch_name:
            return ValidationResult(
                is_valid=False,
                error_message="Branch name cannot be empty",
                error_code="EMPTY_BRANCH_NAME"
            )

        # Check for maximum length
        if len(branch_name) > ValidationPatterns.BRANCH_MAX_LENGTH.value:
            return ValidationResult(
                is_valid=False,
                error_message=f"Branch name too long (max {ValidationPatterns.BRANCH_MAX_LENGTH.value} characters)",
                error_code="BRANCH_NAME_TOO_LONG"
            )

        # Sanitize: remove any control characters first
        sanitized = ''.join(char for char in branch_name if ord(char) >= 32)
        if sanitized != branch_name:
            return ValidationResult(
                is_valid=False,
                error_message="Branch name contains invalid control characters",
                error_code="INVALID_CONTROL_CHARS"
            )

        # Check for invalid characters
        invalid_chars_pattern = ValidationPatterns.BRANCH_INVALID_CHARS.value
        if re.search(invalid_chars_pattern, branch_name):
            invalid_chars = set(re.findall(invalid_chars_pattern, branch_name))
            return ValidationResult(
                is_valid=False,
                error_message=f"Branch name contains invalid characters: {', '.join(sorted(invalid_chars))}",
                error_code="INVALID_BRANCH_CHARS",
                metadata={"invalid_chars": list(invalid_chars)}
            )

        # Check for reserved patterns
        reserved_patterns = [
            (r'\.lock$', 'Cannot end with .lock'),
            (r'^\.', 'Cannot begin with a dot'),
            (r'\.$', 'Cannot end with a dot'),
            (r'\.\.', 'Cannot contain consecutive dots'),
            (r'^-', 'Cannot begin with a hyphen'),
            (r'-$', 'Cannot end with a hyphen'),
            (r'@\{', 'Cannot contain @{'),
            (r'/$', 'Cannot end with slash'),
            (r'^/', 'Cannot begin with slash'),
            (r'//', 'Cannot contain consecutive slashes'),
        ]

        for pattern, reason in reserved_patterns:
            if re.search(pattern, branch_name):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Branch name {reason}",
                    error_code="RESERVED_BRANCH_PATTERN"
                )

        return ValidationResult(is_valid=True)

    @staticmethod
    def validate_commit_message(message: str) -> ValidationResult:
        """
        Validate a git commit message.

        Args:
            message: The commit message to validate

        Returns:
            ValidationResult with validation outcome
        """
        if not message:
            return ValidationResult(
                is_valid=False,
                error_message="Commit message cannot be empty",
                error_code="EMPTY_COMMIT_MESSAGE"
            )

        # Check maximum length for first line
        lines = message.split('\n')
        if len(lines[0]) > ValidationPatterns.COMMIT_MAX_LENGTH.value:
            return ValidationResult(
                is_valid=False,
                error_message=f"First line too long (max {ValidationPatterns.COMMIT_MAX_LENGTH.value} characters)",
                error_code="COMMIT_SUBJECT_TOO_LONG"
            )

        return ValidationResult(is_valid=True)

    @staticmethod
    def validate_conventional_commit(message: str) -> ValidationResult:
        """
        Validate a conventional commit message format.

        Args:
            message: The commit message to validate

        Returns:
            ValidationResult with validation outcome
        """
        if not message:
            return ValidationResult(
                is_valid=False,
                error_message="Commit message cannot be empty",
                error_code="EMPTY_COMMIT_MESSAGE"
            )

        # Conventional commit pattern: type(scope): description
        conventional_pattern = r'^([a-z]+)(\([a-z]+\))?: .+$'
        if not re.match(conventional_pattern, message):
            valid_types = ', '.join([ct.value for ct in CommitTypes])
            return ValidationResult(
                is_valid=False,
                error_message=f"Commit message must follow conventional format: type(scope): description. Valid types: {valid_types}",
                error_code="INVALID_CONVENTIONAL_COMMIT",
                metadata={"valid_types": [ct.value for ct in CommitTypes]}
            )

        # Check if type is valid
        commit_type = message.split('(')[0].split(':')[0]
        try:
            CommitTypes(commit_type)
        except ValueError:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid commit type: {commit_type}",
                error_code="INVALID_COMMIT_TYPE"
            )

        return ValidationResult(is_valid=True)

    @staticmethod
    def validate_tag_name(tag_name: str) -> ValidationResult:
        """
        Validate a git tag name.

        Args:
            tag_name: The tag name to validate

        Returns:
            ValidationResult with validation outcome
        """
        if not tag_name:
            return ValidationResult(
                is_valid=False,
                error_message="Tag name cannot be empty",
                error_code="EMPTY_TAG_NAME"
            )

        # Check maximum length
        if len(tag_name) > ValidationPatterns.TAG_MAX_LENGTH.value:
            return ValidationResult(
                is_valid=False,
                error_message=f"Tag name too long (max {ValidationPatterns.TAG_MAX_LENGTH.value} characters)",
                error_code="TAG_NAME_TOO_LONG"
            )

        # Check for invalid characters
        # Git tags cannot contain: space, tilde, caret, colon, ?, *, [, backslash, control chars
        invalid_chars = r'[\s~^:?*\[\\\x00-\x1f]'
        if re.search(invalid_chars, tag_name):
            return ValidationResult(
                is_valid=False,
                error_message="Tag name contains invalid characters",
                error_code="INVALID_TAG_CHARS"
            )

        # Cannot start or end with dot or slash
        if tag_name.startswith('.') or tag_name.endswith('.'):
            return ValidationResult(
                is_valid=False,
                error_message="Tag name cannot start or end with a dot",
                error_code="INVALID_TAG_FORMAT"
            )

        if tag_name.startswith('/') or tag_name.endswith('/'):
            return ValidationResult(
                is_valid=False,
                error_message="Tag name cannot start or end with a slash",
                error_code="INVALID_TAG_FORMAT"
            )

        # Cannot have consecutive dots
        if '..' in tag_name:
            return ValidationResult(
                is_valid=False,
                error_message="Tag name cannot contain consecutive dots",
                error_code="INVALID_TAG_FORMAT"
            )

        # Cannot end with .lock
        if tag_name.endswith('.lock'):
            return ValidationResult(
                is_valid=False,
                error_message="Tag name cannot end with .lock",
                error_code="INVALID_TAG_FORMAT"
            )

        return ValidationResult(is_valid=True)

    @staticmethod
    def validate_file_path(file_path: str, repo_root: Optional[Path] = None) -> ValidationResult:
        """
        Validate a file path for security (prevent path traversal).

        Args:
            file_path: File path to validate
            repo_root: Repository root directory

        Returns:
            ValidationResult with validation outcome
        """
        if not file_path:
            return ValidationResult(
                is_valid=False,
                error_message="File path cannot be empty",
                error_code="EMPTY_FILE_PATH"
            )

        # Sanitize: remove null bytes
        if '\x00' in file_path:
            return ValidationResult(
                is_valid=False,
                error_message="File path contains null bytes",
                error_code="NULL_BYTES_IN_PATH"
            )

        # Check for path traversal attempts
        if '../' in file_path or '..\\' in file_path:
            return ValidationResult(
                is_valid=False,
                error_message="Path traversal detected",
                error_code="PATH_TRAVERSAL_DETECTED"
            )

        # Check for encoded path traversal attempts
        if '%2e%2e' in file_path.lower() or '%2e%2e%2f' in file_path.lower():
            return ValidationResult(
                is_valid=False,
                error_message="Encoded path traversal detected",
                error_code="ENCODED_PATH_TRAVERSAL"
            )

        # Check for absolute path
        if file_path.startswith('/') or (len(file_path) > 1 and file_path[1] == ':'):
            if repo_root:
                try:
                    path = Path(file_path).resolve()
                    path.relative_to(repo_root.resolve())
                except ValueError:
                    return ValidationResult(
                        is_valid=False,
                        error_message="File path is outside repository",
                        error_code="PATH_OUTSIDE_REPO"
                    )

        # Check maximum length
        if len(file_path) > ValidationPatterns.FILE_MAX_LENGTH.value:
            return ValidationResult(
                is_valid=False,
                error_message=f"File path too long (max {ValidationPatterns.FILE_MAX_LENGTH.value} characters)",
                error_code="FILE_PATH_TOO_LONG"
            )

        return ValidationResult(is_valid=True)

    @staticmethod
    def validate_email(email: str) -> ValidationResult:
        """
        Validate an email address.

        Args:
            email: The email to validate

        Returns:
            ValidationResult with validation outcome
        """
        if not email:
            return ValidationResult(
                is_valid=False,
                error_message="Email cannot be empty",
                error_code="EMPTY_EMAIL"
            )

        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid email format",
                error_code="INVALID_EMAIL_FORMAT"
            )

        return ValidationResult(is_valid=True)

    @staticmethod
    def validate_url(url: str) -> ValidationResult:
        """
        Validate a URL.

        Args:
            url: The URL to validate

        Returns:
            ValidationResult with validation outcome
        """
        if not url:
            return ValidationResult(
                is_valid=False,
                error_message="URL cannot be empty",
                error_code="EMPTY_URL"
            )

        # Basic URL validation
        url_pattern = r'^(https?|ftp)://[^\s/$.?#][^\s]*$'
        if not re.match(url_pattern, url):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid URL format",
                error_code="INVALID_URL_FORMAT"
            )

        return ValidationResult(is_valid=True)

    @staticmethod
    def validate_secrets(output: str) -> ValidationResult:
        """
        Check if output contains potential secrets.

        Args:
            output: The output to check

        Returns:
            ValidationResult with validation outcome
        """
        if not output:
            return ValidationResult(is_valid=True)

        for pattern in SecretPatterns:
            if re.search(pattern.value, output, re.IGNORECASE):
                return ValidationResult(
                    is_valid=False,
                    error_message="Potential secret detected in output",
                    error_code="SECRET_DETECTED",
                    metadata={"pattern_type": pattern.name}
                )

        return ValidationResult(is_valid=True)

    @staticmethod
    def validate_json(json_str: str) -> ValidationResult:
        """
        Validate JSON string.

        Args:
            json_str: The JSON string to validate

        Returns:
            ValidationResult with validation outcome
        """
        if not json_str:
            return ValidationResult(
                is_valid=False,
                error_message="JSON cannot be empty",
                error_code="EMPTY_JSON"
            )

        try:
            import json
            json.loads(json_str)
            return ValidationResult(is_valid=True)
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid JSON: {e}",
                error_code="INVALID_JSON"
            )

    @staticmethod
    def validate_semantic_version(version: str) -> ValidationResult:
        """
        Validate semantic version string.

        Args:
            version: The version string to validate

        Returns:
            ValidationResult with validation outcome
        """
        if not version:
            return ValidationResult(
                is_valid=False,
                error_message="Version cannot be empty",
                error_code="EMPTY_VERSION"
            )

        # Semantic version pattern: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
        semver_pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
        if not re.match(semver_pattern, version):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid semantic version format (expected: MAJOR.MINOR.PATCH)",
                error_code="INVALID_SEMVER"
            )

        return ValidationResult(is_valid=True)

    @staticmethod
    def validate_all(validators: List[Tuple[callable, Any]], fail_fast: bool = True) -> List[ValidationResult]:
        """
        Run multiple validators and return results.

        Args:
            validators: List of (validator_function, value) tuples
            fail_fast: Stop on first validation failure

        Returns:
            List of ValidationResult objects
        """
        results = []

        for validator, value in validators:
            result = validator(value)
            results.append(result)

            if fail_fast and not result.is_valid:
                break

        return results

    @staticmethod
    def combine_results(results: List[ValidationResult]) -> ValidationResult:
        """
        Combine multiple validation results into one.

        Args:
            results: List of ValidationResult objects

        Returns:
            Combined ValidationResult
        """
        # If all are valid, return valid
        if all(r.is_valid for r in results):
            return ValidationResult(is_valid=True)

        # Combine all error messages
        errors = [r.error_message for r in results if not r.is_valid and r.error_message]
        combined_error = '; '.join(errors)

        # Get first error code
        error_code = next((r.error_code for r in results if not r.is_valid and r.error_code), None)

        # Combine metadata
        combined_metadata = {}
        for r in results:
            if r.metadata:
                combined_metadata.update(r.metadata)

        return ValidationResult(
            is_valid=False,
            error_message=combined_error,
            error_code=error_code,
            metadata=combined_metadata
        )