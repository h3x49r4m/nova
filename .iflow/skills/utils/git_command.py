#!/usr/bin/env python3
"""
Shared Git Command Utility
Provides centralized git command execution with timeout handling and error management.
"""

import subprocess
import os
import re
import time
from pathlib import Path
from typing import Tuple, Optional, List, Union, Dict
from .exceptions import GitError, ErrorCode, GitCommandTimeout
from .constants import RetryPolicy, Timeouts, SecretPatterns
from .shared_validators import SharedValidators

# Global metrics collector for git operations
try:
    from .metrics_collector import MetricsCollector
    _metrics = MetricsCollector()
except ImportError:
    _metrics = None


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
        GitError: If command fails
        GitCommandTimeout: If command times out
        GitError: If secrets are detected in output
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
            start_time = time.time()
            result = subprocess.run(
                command_strings,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                shell=False  # Security: always use shell=False
            )
            execution_time = time.time() - start_time
            
            stdout = result.stdout
            stderr = result.stderr
            returncode = result.returncode
            
            # Track metrics if available
            if _metrics:
                command_name = command[0] if command else "unknown"
                _metrics.record_timer(f"git_command_{command_name}", execution_time)
                _metrics.increment_counter("git_commands_total")
                if returncode == 0:
                    _metrics.increment_counter("git_commands_success")
                else:
                    _metrics.increment_counter("git_commands_failed")
            
            # Normalize line endings for cross-platform consistency
            stdout = stdout.replace('\r\n', '\n')
            stderr = stderr.replace('\r\n', '\n')
            
            # Check for secrets in output
            if check_secrets:
                secret_found = check_for_secrets(stdout, stderr)
                if secret_found:
                    raise GitError(
                        f"Secret detected in git command output",
                        code=ErrorCode.SECURITY_VIOLATION
                    )
            
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


def check_for_secrets(stdout: str, stderr: str) -> bool:
    """
    Check git command output for potential secrets using regex patterns.
    
    Args:
        stdout: Standard output from git command
        stderr: Standard error from git command
        
    Returns:
        True if a potential secret is detected, False otherwise
    """
    combined_output = stdout + stderr
    
    for pattern in SecretPatterns:
        if re.search(pattern.value, combined_output, re.IGNORECASE):
            return True
    
    return False


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
    except (GitError, GitCommandTimeout):
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
    except (GitError, GitCommandTimeout):
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

    This function uses the shared validator from shared_validators module
    to ensure consistency across the codebase.

    Args:
        branch_name: The branch name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    result = SharedValidators.validate_branch_name(branch_name)
    return (result.is_valid, result.error_message)


def validate_file_path(file_path: str, repo_root: Optional[Path] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate a file path for security (prevent path traversal).

    This function uses the shared validator from shared_validators module
    to ensure consistency across the codebase.

    Args:
        file_path: File path to validate
        repo_root: Repository root directory

    Returns:
        Tuple of (is_valid, error_message)
    """
    result = SharedValidators.validate_file_path(file_path, repo_root)
    return (result.is_valid, result.error_message)


def get_git_metrics() -> Optional[Dict[str, Any]]:
    """
    Get git operation metrics statistics.

    Returns:
        Dictionary of metrics or None if metrics collector is not available
    """
    if _metrics:
        return _metrics.get_statistics()
    return None


def reset_git_metrics() -> None:
    """Reset all git operation metrics."""
    if _metrics:
        _metrics.reset()


def commit_changes(
    project_path: Path,
    changes_description: str,
    files: Optional[List[str]] = None,
    commit_type: str = "docs",
    commit_scope: str = "general",
    verification: Optional[Dict[str, str]] = None
) -> Tuple[int, str]:
    """
    Standardized commit function with proper metadata and error handling.

    This function provides a consistent way to commit changes across all skills,
    with structured commit messages, file staging, and proper error handling.

    Args:
        project_path: Path to the project directory
        changes_description: Description of changes
        files: List of files to commit (relative to .state directory)
        commit_type: Type of commit (feat, fix, docs, refactor, test, etc.)
        commit_scope: Scope of commit (client, software-engineer, etc.)
        verification: Optional verification info (e.g., {"tests": "passed", "coverage": "85%"})

    Returns:
        Tuple of (exit_code, message)
    """
    try:
        # Get current branch
        code, branch, stderr = run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=project_path)
        if code != 0:
            return code, f"Failed to get current branch: {stderr}"
        
        # Default files to commit
        if files is None:
            files = []
        
        # Stage files
        staged_files = []
        for file in files:
            file_path = project_path / '.state' / file
            if file_path.exists():
                code, _, stderr = run_git_command(['add', str(file_path)], cwd=project_path)
                if code != 0:
                    return code, f"Failed to stage {file}: {stderr}"
                staged_files.append(file)
        
        if not staged_files:
            return 1, "No files to commit"
        
        # Create structured commit message
        commit_message = f"""{commit_type}[{commit_scope}]: {changes_description}

Changes:
"""
        for file in staged_files:
            commit_message += f"- Updated {file}\n"
        
        commit_message += f"""
---
Branch: {branch}

Files changed:
"""
        for file in staged_files:
            commit_message += f"- {project_path}/.state/{file}\n"
        
        # Add verification section if provided
        if verification:
            commit_message += "\nVerification:\n"
            for key, value in verification.items():
                commit_message += f"- {key}: {value}\n"
        
        # Commit changes
        code, stdout, stderr = run_git_command(['commit', '-m', commit_message], cwd=project_path)
        
        if code != 0:
            # Check if it's a "nothing to commit" error (not actually an error)
            if "nothing to commit" in stderr.lower() or "no changes added to commit" in stderr.lower():
                return 0, "No changes to commit"
            return code, f"Failed to commit changes: {stderr}"
        
        return 0, f"Committed {len(staged_files)} file(s) successfully"
        
    except Exception as e:
        return 1, f"Error during commit: {str(e)}"
