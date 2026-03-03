"""Field Validators - Provides regex and pattern-based field validation.

This module provides validators for common field types including
emails, URLs, branch names, commit messages, and more.
"""

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .exceptions import IFlowError, ErrorCode
from .constants import SecretPatterns


class ValidationPattern(Enum):
    """Common validation patterns."""
    EMAIL = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    URL = r"^(https?|ftp)://[^\s/$.?#].[^\s]*$"
    SEMVER = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
    UUID = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    ISO8601 = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$"
    SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    ALPHANUMERIC = r"^[a-zA-Z0-9]+$"
    NUMERIC = r"^\d+$"
    FLOAT = r"^\d+\.?\d*$"
    HEX_COLOR = r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
    IPV4 = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    IPV6 = r"^(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}$"


class FieldValidator:
    """Validates fields using regex patterns and custom rules."""
    
    def __init__(self):
        """Initialize the field validator."""
        self.patterns = {pattern.name: pattern.value for pattern in ValidationPattern}
        self.custom_validators: Dict[str, callable] = {}
    
    def validate_email(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an email address.
        
        Args:
            value: Email address to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "Email is required"
        
        if not re.match(self.patterns["EMAIL"], value):
            return False, f"Invalid email format: {value}"
        
        return True, None
    
    def validate_url(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a URL.
        
        Args:
            value: URL to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "URL is required"
        
        if not re.match(self.patterns["URL"], value):
            return False, f"Invalid URL format: {value}"
        
        return True, None
    
    def validate_semver(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a semantic version string.
        
        Args:
            value: Version string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "Version is required"
        
        if not re.match(self.patterns["SEMVER"], value):
            return False, f"Invalid semantic version format: {value}. Expected format: X.Y.Z"
        
        return True, None
    
    def validate_uuid(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a UUID string.
        
        Args:
            value: UUID to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "UUID is required"
        
        if not re.match(self.patterns["UUID"], value):
            return False, f"Invalid UUID format: {value}"
        
        return True, None
    
    def validate_iso8601(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an ISO8601 datetime string.
        
        Args:
            value: Datetime string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "Datetime is required"
        
        if not re.match(self.patterns["ISO8601"], value):
            return False, f"Invalid ISO8601 format: {value}"
        
        # Try to parse the datetime
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False, f"Invalid datetime value: {value}"
        
        return True, None
    
    def validate_slug(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a slug string.
        
        Args:
            value: Slug to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "Slug is required"
        
        if not re.match(self.patterns["SLUG"], value):
            return False, f"Invalid slug format: {value}. Use lowercase letters, numbers, and hyphens"
        
        return True, None
    
    def validate_branch_name(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a git branch name.
        
        Args:
            value: Branch name to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "Branch name is required"
        
        # Branch name rules
        if value.startswith(".") or value.endswith("/"):
            return False, f"Branch name cannot start with '.' or end with '/': {value}"
        
        if ".." in value:
            return False, f"Branch name cannot contain '..': {value}"
        
        if "//" in value:
            return False, f"Branch name cannot contain '//': {value}"
        
        if " " in value:
            return False, f"Branch name cannot contain spaces: {value}"
        
        if "~" in value or "^" in value or ":" in value:
            return False, f"Branch name cannot contain '~', '^', or ':': {value}"
        
        if value.startswith("-"):
            return False, f"Branch name cannot start with '-': {value}"
        
        # Check length
        if len(value) > 255:
            return False, f"Branch name too long (max 255 characters): {value}"
        
        # Check for special characters
        allowed_pattern = r"^[a-zA-Z0-9\-_./]+$"
        if not re.match(allowed_pattern, value):
            return False, f"Branch name contains invalid characters: {value}"
        
        return True, None
    
    def validate_commit_message(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a commit message.
        
        Args:
            value: Commit message to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "Commit message is required"
        
        # Check for secrets
        for pattern in SecretPatterns:
            if re.search(pattern.value, value, re.IGNORECASE):
                return False, "Commit message may contain sensitive information"
        
        # Check length
        if len(value) > 72:
            return False, f"Commit message too long (max 72 characters): {len(value)}"
        
        return True, None
    
    def validate_file_path(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a file path.
        
        Args:
            value: File path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "File path is required"
        
        # Check for path traversal attempts
        if "../" in value:
            return False, f"File path cannot contain parent directory traversal: {value}"
        
        # Check for absolute path
        if value.startswith("/") or (len(value) > 1 and value[1] == ":"):
            return False, f"Absolute paths not allowed: {value}"
        
        # Check for encoded path traversal
        if "%2e%2e" in value.lower():
            return False, f"File path contains encoded traversal: {value}"
        
        # Check for shell injection patterns
        shell_patterns = [";", "&", "|", "`", "$(", "$(", "\n"]
        for pattern in shell_patterns:
            if pattern in value:
                return False, f"File path contains invalid characters: {value}"
        
        return True, None
    
    def validate_hex_color(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a hexadecimal color code.
        
        Args:
            value: Color code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "Color code is required"
        
        if not re.match(self.patterns["HEX_COLOR"], value):
            return False, f"Invalid hex color format: {value}. Expected format: #RRGGBB or #RGB"
        
        return True, None
    
    def validate_ipv4(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an IPv4 address.
        
        Args:
            value: IP address to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "IP address is required"
        
        if not re.match(self.patterns["IPV4"], value):
            return False, f"Invalid IPv4 format: {value}"
        
        return True, None
    
    def validate_ipv6(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an IPv6 address.
        
        Args:
            value: IP address to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            return False, "IP address is required"
        
        if not re.match(self.patterns["IPV6"], value):
            return False, f"Invalid IPv6 format: {value}"
        
        return True, None
    
    def validate_length(
        self,
        value: str,
        min_length: int = 0,
        max_length: int = 255
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate string length.
        
        Args:
            value: String to validate
            min_length: Minimum length
            max_length: Maximum length
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not value:
            if min_length > 0:
                return False, f"Value is required (minimum {min_length} characters)"
            return True, None
        
        if len(value) < min_length:
            return False, f"Value too short (minimum {min_length} characters): {len(value)}"
        
        if len(value) > max_length:
            return False, f"Value too long (maximum {max_length} characters): {len(value)}"
        
        return True, None
    
    def validate_range(
        self,
        value: Union[int, float],
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate numeric range.
        
        Args:
            value: Numeric value to validate
            min_value: Minimum value
            max_value: Maximum value
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if min_value is not None and value < min_value:
            return False, f"Value too small (minimum {min_value}): {value}"
        
        if max_value is not None and value > max_value:
            return False, f"Value too large (maximum {max_value}): {value}"
        
        return True, None
    
    def validate_enum(
        self,
        value: str,
        allowed_values: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate enum value.
        
        Args:
            value: Value to validate
            allowed_values: List of allowed values
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if value not in allowed_values:
            return False, f"Invalid value: {value}. Allowed: {', '.join(allowed_values)}"
        
        return True, None
    
    def validate_no_secrets(self, value: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a string contains no secrets.
        
        Args:
            value: String to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        for pattern in SecretPatterns:
            if re.search(pattern.value, value, re.IGNORECASE):
                return False, f"Value may contain sensitive information matching pattern: {pattern.name}"
        
        return True, None
    
    def register_custom_validator(
        self,
        name: str,
        validator: callable
    ):
        """
        Register a custom validator.
        
        Args:
            name: Name of the validator
            validator: Validator function that returns (is_valid, error_message)
        """
        self.custom_validators[name] = validator
    
    def validate_custom(
        self,
        name: str,
        value: Any
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate using a custom validator.
        
        Args:
            name: Name of the custom validator
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if name not in self.custom_validators:
            return False, f"Custom validator '{name}' not found"
        
        try:
            return self.custom_validators[name](value)
        except Exception as e:
            return False, f"Custom validator error: {str(e)}"
    
    def validate_field(
        self,
        field_name: str,
        value: Any,
        validators: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Validate a field using multiple validators.
        
        Args:
            field_name: Name of the field
            value: Value to validate
            validators: List of validator names to apply
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        for validator_name in validators:
            is_valid, error = self._run_validator(validator_name, value)
            
            if not is_valid:
                errors.append(f"{field_name}: {error}")
        
        return len(errors) == 0, errors
    
    def _run_validator(
        self,
        name: str,
        value: Any
    ) -> Tuple[bool, Optional[str]]:
        """
        Run a validator by name.
        
        Args:
            name: Name of the validator
            value: Value to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check custom validators first
        if name in self.custom_validators:
            return self.validate_custom(name, value)
        
        # Check built-in validators
        validator_method = getattr(self, f"validate_{name}", None)
        
        if validator_method and callable(validator_method):
            return validator_method(value)
        
        # Check patterns
        if name in self.patterns:
            if re.match(self.patterns[name], str(value)):
                return True, None
            else:
                return False, f"Does not match pattern {name}"
        
        return False, f"Unknown validator: {name}"


def create_validator() -> FieldValidator:
    """Create a field validator instance."""
    return FieldValidator()


def validate_email(value: str) -> Tuple[bool, Optional[str]]:
    """Validate an email address."""
    validator = FieldValidator()
    return validator.validate_email(value)


def validate_branch_name(value: str) -> Tuple[bool, Optional[str]]:
    """Validate a git branch name."""
    validator = FieldValidator()
    return validator.validate_branch_name(value)


def validate_commit_message(value: str) -> Tuple[bool, Optional[str]]:
    """Validate a commit message."""
    validator = FieldValidator()
    return validator.validate_commit_message(value)


def validate_file_path(value: str) -> Tuple[bool, Optional[str]]:
    """Validate a file path."""
    validator = FieldValidator()
    return validator.validate_file_path(value)