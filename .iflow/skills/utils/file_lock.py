#!/usr/bin/env python3
"""
File Locking Utility
Provides cross-platform file locking to prevent race conditions.
"""

import fcntl
import os
from pathlib import Path
from typing import Optional, Union, Any
from contextlib import contextmanager

from .constants import Timeouts


class FileLockError(Exception):
    """Exception raised when file locking fails."""
    pass


class FileLock:
    """
    Cross-platform file lock using fcntl (Unix) and msvcrt (Windows).
    
    Usage:
        with FileLock('/path/to/file.lock'):
            # Critical section
            pass
    """
    
    def __init__(self, lock_file: Union[str, Path], timeout: float = 30.0):
        """
        Initialize file lock.
        
        Args:
            lock_file: Path to lock file
            timeout: Timeout in seconds to acquire lock
        """
        self.lock_file = Path(lock_file)
        self.timeout = timeout
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock_fd: Optional[int] = None
    
    def acquire(self) -> bool:
        """
        Acquire the lock with timeout.
        
        Returns:
            True if lock acquired, False otherwise
        """
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            try:
                self._lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_WRONLY)
                
                # Try to acquire exclusive lock
                try:
                    fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # Write our PID to the lock file
                    os.write(self._lock_fd, str(os.getpid()).encode())
                    return True
                except (IOError, BlockingIOError):
                    # Lock is held by another process
                    os.close(self._lock_fd)
                    self._lock_fd = None
                    time.sleep(0.1)
                    
            except OSError as e:
                if self._lock_fd is not None:
                    os.close(self._lock_fd)
                    self._lock_fd = None
                raise FileLockError(f"Failed to create lock file: {e}")
        
        return False
    
    def release(self) -> None:
        """Release the lock."""
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
                self._lock_fd = None
            except OSError:
                pass
            
            # Try to remove lock file
            try:
                self.lock_file.unlink()
            except OSError:
                pass
    
    def __enter__(self) -> 'FileLock':
        """Enter context manager."""
        if not self.acquire():
            raise FileLockError(f"Failed to acquire lock on {self.lock_file} within {self.timeout} seconds")
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        self.release()
    
    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.release()


@contextmanager
def locked_file(file_path: Union[str, Path], mode: str = 'r', timeout: float = 30.0):
    """
    Context manager that locks a file while working with it.
    
    Args:
        file_path: Path to the file
        mode: File open mode
        timeout: Lock timeout in seconds
        
    Yields:
        File object
        
    Example:
        with locked_file('data.json', 'w') as f:
            json.dump(data, f)
    """
    file_path = Path(file_path)
    lock_file = file_path.with_suffix(file_path.suffix + '.lock')
    
    with FileLock(lock_file, timeout=timeout):
        with open(file_path, mode) as f:
            yield f


def read_locked_json(file_path: Union[str, Path], timeout: float = 30.0) -> dict:
    """
    Read JSON file with file locking.
    
    Args:
        file_path: Path to JSON file
        timeout: Lock timeout in seconds
        
    Returns:
        Parsed JSON dictionary
    """
    with locked_file(file_path, 'r', timeout=timeout) as f:
        return json.load(f)


def write_locked_json(file_path: Union[str, Path], data: dict, timeout: float = 30.0) -> None:
    """
    Write JSON file with file locking.
    
    Args:
        file_path: Path to JSON file
        data: Dictionary to write
        timeout: Lock timeout in seconds
    """
    with locked_file(file_path, 'w', timeout=timeout) as f:
        json.dump(data, f, indent=2)