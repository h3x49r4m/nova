#!/usr/bin/env python3
"""
Version validation utilities.
Checks Python and Git version requirements.
"""

import sys
import subprocess
from typing import Tuple, Optional
from .exceptions import ValidationError, ErrorCode, ErrorCategory
from .constants import SystemRequirements


class VersionChecker:
    """Version checker utility class."""
    
    def __init__(self):
        """Initialize version checker."""
        pass
    
    def check_python(self, min_version: Tuple[int, int] = None) -> Tuple[bool, Optional[str]]:
        """Check Python version."""
        return check_python_version(min_version)
    
    def check_git(self, min_version: Tuple[int, int, int] = None) -> Tuple[bool, Optional[str]]:
        """Check Git version."""
        return check_git_version(min_version)
    
    def validate_system(self, strict: bool = False) -> Tuple[bool, list]:
        """Validate system requirements."""
        return validate_system_requirements(strict)


def check_python_version(min_version: Tuple[int, int] = None) -> Tuple[bool, Optional[str]]:
    """
    Check if Python version meets minimum requirements.
    
    Args:
        min_version: Minimum required version as (major, minor) tuple.
                   Defaults to SystemRequirements.PYTHON_MIN_VERSION.value
    
    Returns:
        Tuple of (is_compatible, error_message)
    """
    if min_version is None:
        min_version = SystemRequirements.PYTHON_MIN_VERSION.value
    
    current_version = (sys.version_info.major, sys.version_info.minor)
    
    if current_version < min_version:
        error_msg = (
            f"Python {min_version[0]}.{min_version[1]} or higher required. "
            f"Current version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        return False, error_msg
    
    return True, None


def check_git_version(min_version: Tuple[int, int, int] = None) -> Tuple[bool, Optional[str]]:
    """
    Check if Git version meets minimum requirements.
    
    Args:
        min_version: Minimum required version as (major, minor, patch) tuple.
                   Defaults to SystemRequirements.GIT_MIN_VERSION.value
    
    Returns:
        Tuple of (is_compatible, error_message)
    """
    if min_version is None:
        min_version = SystemRequirements.GIT_MIN_VERSION.value
    
    try:
        # Run git --version
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return False, "Git not found or not executable"
        
        # Parse version string
        version_str = result.stdout.strip()
        # Expected format: "git version 2.39.5" or similar
        parts = version_str.split()
        if len(parts) < 3:
            return False, f"Unable to parse Git version: {version_str}"
        
        version_parts = parts[2].split('.')
        if len(version_parts) < 3:
            return False, f"Invalid Git version format: {parts[2]}"
        
        current_version = (
            int(version_parts[0]),
            int(version_parts[1]),
            int(version_parts[2].split('-')[0])  # Handle versions like "2.39.5-rc1"
        )
        
        if current_version < min_version:
            error_msg = (
                f"Git {min_version[0]}.{min_version[1]}.{min_version[2]} or higher required. "
                f"Current version: {parts[2]}"
            )
            return False, error_msg
        
        return True, None
        
    except subprocess.TimeoutExpired:
        return False, "Git version check timed out"
    except FileNotFoundError:
        return False, "Git not found. Please install Git."
    except ValueError as e:
        return False, f"Error parsing Git version: {str(e)}"
    except Exception as e:
        return False, f"Error checking Git version: {str(e)}"


def validate_system_requirements(strict: bool = False) -> Tuple[bool, list]:
    """
    Validate all system requirements (Python and Git versions).
    
    Args:
        strict: If True, raises exceptions on validation errors.
                If False, returns results without raising.
    
    Returns:
        Tuple of (all_compatible, list_of_error_messages)
    
    Raises:
        ValidationError: If strict=True and validation fails
    """
    errors = []
    
    # Check Python version
    python_ok, python_error = check_python_version()
    if not python_ok:
        errors.append(python_error)
        if strict:
            raise ValidationError(
                python_error,
                ErrorCode.VERSION_MISMATCH,
                ErrorCategory.SYSTEM
            )
    
    # Check Git version
    git_ok, git_error = check_git_version()
    if not git_ok:
        errors.append(git_error)
        if strict:
            raise ValidationError(
                git_error,
                ErrorCode.VERSION_MISMATCH,
                ErrorCategory.SYSTEM
            )
    
    return len(errors) == 0, errors


def print_version_info() -> None:
    """Print current Python and Git version information."""
    print("System Version Information:")
    print(f"  Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"  Python Location: {sys.executable}")
    
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"  Git: {result.stdout.strip()}")
        else:
            print("  Git: Not available")
    except Exception as e:
        print(f"  Git: Not available (Error: {e})")
    
    # Check requirements
    print("\nVersion Requirements:")
    print(f"  Python Minimum: {SystemRequirements.PYTHON_MIN_VERSION.value[0]}.{SystemRequirements.PYTHON_MIN_VERSION.value[1]}")
    print(f"  Git Minimum: {SystemRequirements.GIT_MIN_VERSION.value[0]}.{SystemRequirements.GIT_MIN_VERSION.value[1]}.{SystemRequirements.GIT_MIN_VERSION.value[2]}")
    
    # Validate
    all_ok, errors = validate_system_requirements()
    print("\nValidation:")
    if all_ok:
        print("  ✓ All system requirements met")
    else:
        print("  ✗ System requirements not met:")
        for error in errors:
            print(f"    - {error}")


def ensure_requirements(strict: bool = False) -> None:
    """
    Ensure system requirements are met, exiting if not.
    
    Args:
        strict: If True, raises exceptions on validation errors.
    
    Raises:
        SystemExit: If requirements not met
    """
    all_ok, errors = validate_system_requirements(strict=strict)
    
    if not all_ok:
        print("System Requirements Not Met:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print("\nPlease update your system to meet the minimum requirements.", file=sys.stderr)
        sys.exit(1)


# Auto-validate on import (optional, can be disabled)
# Uncomment to automatically check requirements when this module is imported
# if __name__ != "__main__":
#     ensure_requirements(strict=False)
