#!/usr/bin/env python3
"""
Input Sanitization Utility
Provides centralized input validation and sanitization to prevent injection attacks.
"""

import re
import html
from typing import Optional, List, Callable
from pathlib import Path


class InputSanitizer:
    """Utility class for sanitizing user input."""

    # Dangerous patterns for command injection
    COMMAND_INJECTION_PATTERNS = [
        r'[;&|`$]',  # Shell metacharacters
        r'\$\(',     # Command substitution
        r'<[^>]*>',  # HTML/XML tags (potential XSS)
        r'\.\./',    # Path traversal
        r'\\\\',     # Escaped characters
    ]

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"['\"]\s*(OR|AND|XOR)\s*['\"]",
        r"['\"]\s*(=|!=|<>|<|>)\s*['\"]",
        r";\s*(DROP|DELETE|INSERT|UPDATE|EXEC|UNION)\s",
        r"--\s*$",  # SQL comments
        r"/\\*.*\\*/",  # SQL block comments
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'on\w+\s*=',  # Event handlers like onclick=
        r'javascript:',
        r'data:text/html',
    ]

    # Allowed characters for different input types
    ALLOWED_BRANCH_CHARS = r'[a-zA-Z0-9_\-/\.]'
    ALLOWED_ALPHANUMERIC = r'[a-zA-Z0-9_\-\.@]'
    ALLOWED_PATH_CHARS = r'[a-zA-Z0-9_\-/\.]'

    @staticmethod
    def sanitize_string(
        input_str: str,
        allowed_chars: Optional[str] = None,
        max_length: Optional[int] = None,
        remove_null: bool = True
    ) -> str:
        """
        Sanitize a string input by removing dangerous characters.

        Args:
            input_str: The input string to sanitize
            allowed_chars: Regex pattern for allowed characters
            max_length: Maximum allowed length
            remove_null: Whether to remove null bytes

        Returns:
            Sanitized string

        Raises:
            ValueError: If input contains invalid characters or exceeds max length
        """
        if not isinstance(input_str, str):
            raise ValueError("Input must be a string")

        # Remove null bytes
        if remove_null:
            input_str = input_str.replace('\x00', '')

        # Check for null bytes after removal
        if '\x00' in input_str:
            raise ValueError("Input contains null bytes")

        # Check max length
        if max_length is not None and len(input_str) > max_length:
            raise ValueError(f"Input exceeds maximum length of {max_length}")

        # Remove control characters except newline and tab
        input_str = ''.join(char for char in input_str if ord(char) >= 32 or char in '\n\t')

        # Apply allowed character filter
        if allowed_chars:
            # Build a pattern that matches disallowed characters
            pattern = f'[^{allowed_chars}]'
            if re.search(pattern, input_str):
                # Extract disallowed characters for error message
                disallowed = set(re.findall(pattern, input_str))
                raise ValueError(
                    f"Input contains disallowed characters: {', '.join(sorted(disallowed))}"
                )

        return input_str.strip()

    @staticmethod
    def sanitize_branch_name(branch_name: str) -> str:
        """
        Sanitize a git branch name.

        Args:
            branch_name: The branch name to sanitize

        Returns:
            Sanitized branch name

        Raises:
            ValueError: If branch name is invalid
        """
        # Basic sanitization
        sanitized = InputSanitizer.sanitize_string(
            branch_name,
            allowed_chars=InputSanitizer.ALLOWED_BRANCH_CHARS,
            max_length=255
        )

        # Git-specific rules
        if sanitized.startswith('.') or sanitized.endswith('.'):
            raise ValueError("Branch name cannot start or end with a dot")

        if '..' in sanitized:
            raise ValueError("Branch name cannot contain consecutive dots")

        if sanitized.startswith('-') or sanitized.endswith('-'):
            raise ValueError("Branch name cannot start or end with a hyphen")

        if '@{' in sanitized:
            raise ValueError("Branch name cannot contain '@{'")

        if sanitized.endswith('.lock'):
            raise ValueError("Branch name cannot end with '.lock'")

        return sanitized

    @staticmethod
    def sanitize_commit_message(message: str) -> str:
        """
        Sanitize a git commit message.

        Args:
            message: The commit message to sanitize

        Returns:
            Sanitized commit message

        Raises:
            ValueError: If commit message is invalid
        """
        # Allow most characters but limit length
        sanitized = InputSanitizer.sanitize_string(
            message,
            max_length=10000  # Reasonable max for commit messages
        )

        # Remove potential command injection
        for pattern in InputSanitizer.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise ValueError("Commit message contains potentially dangerous characters")

        return sanitized

    @staticmethod
    def sanitize_file_path(file_path: str, base_dir: Optional[Path] = None) -> str:
        """
        Sanitize a file path to prevent path traversal.

        Args:
            file_path: The file path to sanitize
            base_dir: Base directory for resolving relative paths

        Returns:
            Sanitized and resolved file path

        Raises:
            ValueError: If path is invalid or contains traversal
        """
        # Remove null bytes
        sanitized = InputSanitizer.sanitize_string(file_path, remove_null=True)

        # Check for path traversal
        if '../' in sanitized or '..\\' in sanitized:
            raise ValueError("Path traversal detected")

        if '~' in sanitized:
            raise ValueError("Tilde expansion not allowed")

        # Check for absolute path if base_dir provided
        if base_dir:
            try:
                path = Path(sanitized)
                if path.is_absolute():
                    resolved = path.resolve()
                    try:
                        resolved.relative_to(base_dir.resolve())
                    except ValueError:
                        raise ValueError("Absolute path is outside base directory")
                else:
                    resolved = (base_dir / path).resolve()
            except Exception as e:
                raise ValueError(f"Invalid path: {e}")

            return str(resolved)

        return sanitized

    @staticmethod
    def sanitize_username(username: str) -> str:
        """
        Sanitize a username for commit attribution.

        Args:
            username: The username to sanitize

        Returns:
            Sanitized username

        Raises:
            ValueError: If username is invalid
        """
        sanitized = InputSanitizer.sanitize_string(
            username,
            allowed_chars=InputSanitizer.ALLOWED_ALPHANUMERIC,
            max_length=100
        )

        return sanitized

    @staticmethod
    def sanitize_email(email: str) -> str:
        """
        Sanitize an email address.

        Args:
            email: The email to sanitize

        Returns:
            Sanitized email

        Raises:
            ValueError: If email is invalid
        """
        sanitized = InputSanitizer.sanitize_string(email, max_length=255)

        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, sanitized):
            raise ValueError("Invalid email format")

        return sanitized.lower()

    @staticmethod
    def check_command_injection(input_str: str) -> bool:
        """
        Check if input contains potential command injection patterns.

        Args:
            input_str: The input to check

        Returns:
            True if injection detected, False otherwise
        """
        for pattern in InputSanitizer.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def check_sql_injection(input_str: str) -> bool:
        """
        Check if input contains potential SQL injection patterns.

        Args:
            input_str: The input to check

        Returns:
            True if injection detected, False otherwise
        """
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def check_xss(input_str: str) -> bool:
        """
        Check if input contains potential XSS patterns.

        Args:
            input_str: The input to check

        Returns:
            True if XSS detected, False otherwise
        """
        for pattern in InputSanitizer.XSS_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE | re.DOTALL):
                return True
        return False

    @staticmethod
    def sanitize_html(input_str: str) -> str:
        """
        Escape HTML special characters to prevent XSS.

        Args:
            input_str: The input string

        Returns:
            HTML-escaped string
        """
        return html.escape(input_str)

    @staticmethod
    def sanitize_json(input_str: str) -> str:
        """
        Validate and sanitize JSON input.

        Args:
            input_str: The JSON string

        Returns:
            Sanitized JSON string

        Raises:
            ValueError: If JSON is invalid
        """
        import json

        try:
            # Try to parse the JSON
            parsed = json.loads(input_str)

            # Re-serialize to ensure it's clean
            return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    @staticmethod
    def sanitize_list(
        items: List[str],
        item_sanitizer: Optional[Callable[[str], str]] = None
    ) -> List[str]:
        """
        Sanitize a list of string items.

        Args:
            items: List of strings to sanitize
            item_sanitizer: Optional custom sanitizer function for each item

        Returns:
            List of sanitized strings

        Raises:
            ValueError: If any item is invalid
        """
        if not isinstance(items, list):
            raise ValueError("Input must be a list")

        sanitized = []
        for item in items:
            if not isinstance(item, str):
                raise ValueError("All items must be strings")

            if item_sanitizer:
                sanitized.append(item_sanitizer(item))
            else:
                sanitized.append(InputSanitizer.sanitize_string(item))

        return sanitized