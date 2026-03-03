#!/usr/bin/env python3
"""
Shared Git Command Utility
Provides centralized git command execution with timeout handling and error management.
"""

import subprocess
import os
from pathlib import Path
from typing import Tuple, Optional, List, TypeVar, ParamSpec
import sys
from exceptions import GitError, ErrorCode, ErrorCategory, wrap_error
from constants import RetryPolicy


def run_git_command(
    command: List[str],
    cwd: Optional[Union[str, Path]] = None,
    timeout: Optional[int] = None,
    env: Optional[Dict[str, str]] = None,
    check_secrets: bool = True,
    retry_on_failure: bool = False
) -> Tuple[int, str, str]:
    """
    Run a git command with error handling and optional retry logic.
    
    Args:
        command: Git command as a list of strings
        cwd: Working directory for the command
        timeout: Command timeout in seconds
        env: Environment variables for the command
        check_secrets: Whether to check output for secrets
        retry_on_failure: Whether to retry on transient failures
        
    Returns:
        Tuple of (return_code, stdout, stderr)
        
    Raises:
        GitCommandError: If command fails
        GitCommandTimeout: If command times out
        SecurityError: If secrets are detected in output
    """
    if cwd is None:
        cwd = os.getcwd()
    
    if timeout is None:
        timeout = Timeouts.GIT_DEFAULT.value
    
    if env is None:
        env = os.environ.copy()
    
    # Validate working directory
    cwd_path = Path(cwd)
    is_valid, error_msg = validate_file_path(str(cwd_path))
    if not is_valid:
        raise GitError(
            f"Invalid working directory: {error_msg}",
            code=ErrorCode.VALIDATION_ERROR
        )
    
    if not cwd_path.exists():
        raise GitError(
            f"Working directory does not exist: {cwd}",
            code=ErrorCode.FILE_NOT_FOUND
        )
    
    if not cwd_path.is_dir():
        raise GitError(
            f"Working directory is not a directory: {cwd}",
            code=ErrorCode.INVALID_ARGUMENT
        )
    
    # Retry logic
    max_retries = RetryPolicy.MAX_ATTEMPTS.value if retry_on_failure else 1
    base_delay = RetryPolicy.INITIAL_DELAY.value
    
    # Convert command items to strings
    command_strings = ['git'] + [str(c) for c in command]
    
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                command_strings,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                shell=False  # Security: always use shell=False
            )
            
            stdout = result.stdout
            stderr = result.stderr
            returncode = result.returncode
            
            # Normalize line endings for cross-platform consistency
            stdout = stdout.replace('\r\n', '\n')
            stderr = stderr.replace('\r\n', '\n')
            
            # Check for secrets in output
            # TODO: Implement check_for_secrets function
            # if check_secrets:
            #     secret_found = check_for_secrets(stdout, stderr)
            #     if secret_found:
            #         raise GitError(
            #             f"Secret detected in git command output",
            #             code=ErrorCode.SECURITY_VIOLATION
            #         )
            
            return returncode, stdout, stderr
            
        except subprocess.TimeoutExpired as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
                continue
            raise GitCommandTimeout(
                f"Git command timed out after {timeout} seconds: {' '.join(command)}",
                command=command,
                timeout=timeout
            )
        except subprocess.CalledProcessError as e:
            if attempt < max_retries - 1 and retry_on_failure:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
                continue
            return e.returncode, e.stdout or '', e.stderr or ''
        except FileNotFoundError:
            raise GitError(
                "Git is not installed or not in PATH",
                code=ErrorCode.DEPENDENCY_ERROR
            )
        except Exception as e:
            if attempt < max_retries - 1 and retry_on_failure:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
                continue
            raise GitError(
                f"Unexpected error running git command: {str(e)}",
                code=ErrorCode.UNKNOWN_ERROR,
                cause=e
            )
    
    # Should never reach here
    raise GitError(
        "Git command failed after all retry attempts",
        code=ErrorCode.UNKNOWN_ERROR
    )


def validate_git_repo(cwd: Optional[Path] = None) -> bool:
    """
    Check if current directory is a valid git repository.
    
    Args:
        cwd: Working directory to check
    
    Returns:
        True if valid git repo, False otherwise
    """
    try:
        returncode, _, _ = run_git_command(['rev-parse', '--git-dir'], cwd=cwd, timeout=10)
        return returncode == 0
    except (GitCommandError, GitCommandTimeout):
        return False


def get_current_branch(cwd: Optional[Path] = None) -> str:
    """
    Get the current branch name.
    
    Args:
        cwd: Working directory
    
    Returns:
        Current branch name or 'unknown' if error
    """
    try:
        code, stdout, _ = run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=cwd, timeout=10)
        return stdout.strip() if code == 0 else 'unknown'
    except (GitCommandError, GitCommandTimeout):
        return 'unknown'


def get_repo_root(cwd: Optional[Path] = None) -> Optional[Path]:
    """
    Get the git repository root directory.
    
    Args:
        cwd: Working directory
    
    Returns:
        Path to repo root or None if not in a git repo
    """
    try:
        code, stdout, _ = run_git_command(['rev-parse', '--show-toplevel'], cwd=cwd, timeout=10)
        if code == 0:
            return Path(stdout.strip())
        return None
    except (GitCommandError, GitCommandTimeout):
        return None


def validate_branch_name(branch_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a git branch name according to git naming rules.
    
    Args:
        branch_name: The branch name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not branch_name:
        return False, "Branch name cannot be empty"
    
    # Check for maximum length
    if len(branch_name) > ValidationPatterns.BRANCH_MAX_LENGTH.value:
        return False, f"Branch name too long (max {ValidationPatterns.BRANCH_MAX_LENGTH.value} characters)"
    
    # Sanitize: remove any control characters first
    sanitized = ''.join(char for char in branch_name if ord(char) >= 32)
    if sanitized != branch_name:
        return False, "Branch name contains invalid control characters"
    
    # Check for invalid characters
    invalid_chars_pattern = ValidationPatterns.BRANCH_INVALID_CHARS.value
    if re.search(invalid_chars_pattern, branch_name):
        invalid_chars = set(re.findall(invalid_chars_pattern, branch_name))
        return False, f"Branch name contains invalid characters: {', '.join(sorted(invalid_chars))}"
    
    # Check for reserved names
    reserved_patterns = [
        r'\.lock',
    ]
    
    for pattern in reserved_patterns:
        if re.match(pattern, branch_name):
            return False, f"Branch name '{branch_name}' matches reserved pattern '{pattern}'"
    
    return True, None


def validate_file_path(file_path: str, repo_root: Optional[Path] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate a file path for security (prevent path traversal).
    
    Args:
        file_path: File path to validate
        repo_root: Repository root directory
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_path:
        return False, "File path cannot be empty"
    
    # Sanitize: remove null bytes and other dangerous characters
    if '\x00' in file_path:
        return False, "File path contains null bytes"
    
    # Check for path traversal attempts
    if '../' in file_path or '..\\' in file_path:
        return False, "Path traversal detected"
    
    # Check for encoded path traversal attempts
    if '%2e%2e' in file_path.lower() or '%2e%2e%2f' in file_path.lower():
        return False, "Encoded path traversal detected"
    
    if file_path.startswith('/') or (len(file_path) > 1 and file_path[1] == ':'):
        # Absolute path - resolve and check if within repo
        try:
            path = Path(file_path).resolve()
            if repo_root:
                try:
                    path.relative_to(repo_root)
                except ValueError:
                    return False, "File path is outside repository"
        except Exception:
            return False, "Invalid file path"
    
    # Check for shell command injection patterns
    shell_injection_patterns = [';', '&', '|', '`', '$(', '<', '>', '\n', '\r']
    for pattern in shell_injection_patterns:
        if pattern in file_path and file_path.strip().endswith('.py'):
            # Only suspicious if it looks like a command in a code file
            return False, f"Potential shell injection detected: '{pattern}'"
    
    return True, None
