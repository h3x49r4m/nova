"""Async Git Command Module - Provides asynchronous git operations with streaming support.

This module implements async git operations for better performance and
streaming support for large files.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, List, Tuple, AsyncIterator, Union
import hashlib

from .exceptions import GitError, ErrorCode, SecurityError
from .constants import SecretPatterns, Timeouts


class AsyncGitCommand:
    """Async git command executor with streaming support."""

    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize async git command executor.

        Args:
            repo_root: Root directory of the git repository
        """
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()

    async def run_git_command(
        self,
        command: List[str],
        cwd: Optional[Union[str, Path]] = None,
        timeout: Optional[int] = None,
        env: Optional[dict] = None,
        check_secrets: bool = True,
        stream_output: bool = False
    ) -> Tuple[int, str, str]:
        """
        Run a git command asynchronously.

        Args:
            command: Git command to execute (e.g., ['git', 'status'])
            cwd: Working directory for the command
            timeout: Command timeout in seconds
            env: Environment variables for the command
            check_secrets: Whether to check for secrets in output
            stream_output: Whether to stream output (for large outputs)

        Returns:
            Tuple of (exit_code, stdout, stderr)

        Raises:
            GitError: If git command fails or contains secrets
        """
        if timeout is None:
            timeout = Timeouts.GIT_DEFAULT.value

        working_dir = Path(cwd) if cwd else self.repo_root

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env or os.environ.copy()
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                raise GitError(
                    f"Git command timed out after {timeout}s: {' '.join(command)}",
                    code=ErrorCode.GIT_TIMEOUT
                )

            # Decode output
            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')

            # Check for secrets if enabled
            if check_secrets:
                self._check_for_secrets(stdout_text, stderr_text)

            return process.returncode or 0, stdout_text, stderr_text

        except FileNotFoundError:
            raise GitError(
                f"Git command not found: {command[0]}",
                code=ErrorCode.GIT_NOT_FOUND
            )
        except Exception as e:
            if isinstance(e, GitError):
                raise
            raise GitError(
                f"Failed to run git command: {' '.join(command)}",
                code=ErrorCode.GIT_COMMAND_FAILED,
                cause=e
            )

    async def run_git_command_stream(
        self,
        command: List[str],
        cwd: Optional[Union[str, Path]] = None,
        timeout: Optional[int] = None,
        env: Optional[dict] = None,
        chunk_size: int = 8192,
        check_secrets: bool = True
    ) -> AsyncIterator[Tuple[int, str, str]]:
        """
        Run a git command with streaming output.

        Args:
            command: Git command to execute
            cwd: Working directory for the command
            timeout: Command timeout in seconds
            env: Environment variables for the command
            chunk_size: Size of chunks to read
            check_secrets: Whether to check for secrets in output

        Yields:
            Tuple of (exit_code, stdout_chunk, stderr_chunk)

        Raises:
            GitError: If git command fails or contains secrets
        """
        if timeout is None:
            timeout = Timeouts.GIT_DEFAULT.value

        working_dir = Path(cwd) if cwd else self.repo_root

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env or os.environ.copy()
            )

            stdout_buffer = []
            stderr_buffer = []

            # Create tasks for reading stdout and stderr
            async def read_stream(stream, buffer):
                while True:
                    chunk = await stream.read(chunk_size)
                    if not chunk:
                        break
                    buffer.append(chunk)
                    yield chunk.decode('utf-8', errors='replace')

            # Stream output
            stdout_reader = read_stream(process.stdout, stdout_buffer)
            stderr_reader = read_stream(process.stderr, stderr_buffer)

            # Wait for completion with timeout
            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                raise GitError(
                    f"Git command timed out after {timeout}s: {' '.join(command)}",
                    code=ErrorCode.GIT_TIMEOUT
                )

            # Yield final results
            stdout_text = ''.join(chunk async for chunk in stdout_reader)
            stderr_text = ''.join(chunk async for chunk in stderr_reader)

            # Check for secrets if enabled
            if check_secrets:
                self._check_for_secrets(stdout_text, stderr_text)

            yield (process.returncode or 0, stdout_text, stderr_text)

        except FileNotFoundError:
            raise GitError(
                f"Git command not found: {command[0]}",
                code=ErrorCode.GIT_NOT_FOUND
            )
        except Exception as e:
            if isinstance(e, GitError):
                raise
            raise GitError(
                f"Failed to run git command: {' '.join(command)}",
                code=ErrorCode.GIT_COMMAND_FAILED,
                cause=e
            )

    async def run_git_commands_parallel(
        self,
        commands: List[List[str]],
        cwd: Optional[Union[str, Path]] = None,
        timeout: Optional[int] = None,
        check_secrets: bool = True
    ) -> List[Tuple[int, str, str]]:
        """
        Run multiple git commands in parallel.

        Args:
            commands: List of git commands to execute
            cwd: Working directory for the commands
            timeout: Timeout for each command
            check_secrets: Whether to check for secrets in output

        Returns:
            List of tuples (exit_code, stdout, stderr) for each command

        Raises:
            GitError: If any git command fails
        """
        tasks = [
            self.run_git_command(cmd, cwd, timeout, check_secrets=check_secrets)
            for cmd in commands
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                raise GitError(
                    f"Git command {i} failed: {commands[i]}",
                    code=ErrorCode.GIT_COMMAND_FAILED,
                    cause=result
                )

        return results  # type: ignore

    def _check_for_secrets(self, stdout: str, stderr: str) -> None:
        """
        Check git command output for secrets.

        Args:
            stdout: Standard output from git command
            stderr: Standard error from git command

        Raises:
            SecurityError: If secrets are detected
        """
        combined_output = stdout + stderr
        combined_lower = combined_output.lower()

        for pattern in SecretPatterns:
            match = pattern.value.search(combined_lower)
            if match:
                raise SecurityError(
                    f"Secret detected in git command output: {pattern.name}",
                    code=ErrorCode.SECURITY_VIOLATION
                )


async def get_current_branch_async(
    repo_root: Optional[Path] = None
) -> str:
    """
    Get the current git branch name asynchronously.

    Args:
        repo_root: Root directory of the git repository

    Returns:
        Current branch name

    Raises:
        GitError: If git command fails
    """
    git_cmd = AsyncGitCommand(repo_root)
    exit_code, stdout, stderr = await git_cmd.run_git_command(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
    )

    if exit_code != 0:
        raise GitError(
            f"Failed to get current branch: {stderr}",
            code=ErrorCode.GIT_COMMAND_FAILED
        )

    return stdout.strip()


async def get_repo_root_async() -> Path:
    """
    Get the root directory of the git repository asynchronously.

    Returns:
        Path to the repository root

    Raises:
        GitError: If git command fails
    """
    git_cmd = AsyncGitCommand()
    exit_code, stdout, stderr = await git_cmd.run_git_command(
        ['git', 'rev-parse', '--show-toplevel']
    )

    if exit_code != 0:
        raise GitError(
            f"Failed to get repository root: {stderr}",
            code=ErrorCode.GIT_COMMAND_FAILED
        )

    return Path(stdout.strip())


async def validate_git_repo_async(repo_root: Optional[Path] = None) -> bool:
    """
    Validate that a directory is a git repository asynchronously.

    Args:
        repo_root: Directory to check

    Returns:
        True if directory is a git repository
    """
    git_cmd = AsyncGitCommand(repo_root)
    try:
        exit_code, _, _ = await git_cmd.run_git_command(['git', 'rev-parse', '--git-dir'])
        return exit_code == 0
    except GitError:
        return False


async def stream_file_async(
    file_path: Path,
    chunk_size: int = 8192
) -> AsyncIterator[bytes]:
    """
    Stream a file asynchronously in chunks.

    Args:
        file_path: Path to the file to stream
        chunk_size: Size of chunks to read

    Yields:
        File chunks as bytes
    """
    loop = asyncio.get_event_loop()

    with open(file_path, 'rb') as f:
        while True:
            chunk = await loop.run_in_executor(None, f.read, chunk_size)
            if not chunk:
                break
            yield chunk


async def calculate_file_hash_async(
    file_path: Path,
    algorithm: str = 'sha256'
) -> str:
    """
    Calculate file hash asynchronously with streaming.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use (default: sha256)

    Returns:
        Hexadecimal hash string
    """
    hash_obj = hashlib.new(algorithm)

    async for chunk in stream_file_async(file_path):
        hash_obj.update(chunk)

    return hash_obj.hexdigest()


# Convenience functions for backward compatibility
async def run_git_command_async(
    command: List[str],
    cwd: Optional[Union[str, Path]] = None,
    timeout: Optional[int] = None,
    env: Optional[dict] = None,
    check_secrets: bool = True
) -> Tuple[int, str, str]:
    """
    Convenience function to run a git command asynchronously.

    Args:
        command: Git command to execute
        cwd: Working directory for the command
        timeout: Command timeout in seconds
        env: Environment variables for the command
        check_secrets: Whether to check for secrets in output

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    git_cmd = AsyncGitCommand(cwd)
    return await git_cmd.run_git_command(
        command,
        cwd=cwd,
        timeout=timeout,
        env=env,
        check_secrets=check_secrets
    )