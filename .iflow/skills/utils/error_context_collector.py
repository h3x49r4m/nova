"""Error Context Collector - Collects and aggregates debugging context for errors.

This module provides functionality for automatically collecting relevant
context information when errors occur to aid in debugging.
"""

import inspect
import os
import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from functools import wraps

from .exceptions import IFlowError


class ErrorContext:
    """Represents collected error context."""
    
    def __init__(self):
        """Initialize an empty error context."""
        self.timestamp: str = ""
        self.system_info: Dict[str, str] = {}
        self.environment: Dict[str, str] = {}
        self.call_stack: List[Dict[str, Any]] = []
        self.variables: Dict[str, Any] = {}
        self.files: Dict[str, Dict[str, Any]] = {}
        self.process_info: Dict[str, Any] = {}
        self.custom_context: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "timestamp": self.timestamp,
            "system_info": self.system_info,
            "environment": self.environment,
            "call_stack": self.call_stack,
            "variables": self.variables,
            "files": self.files,
            "process_info": self.process_info,
            "custom_context": self.custom_context
        }


class ErrorContextCollector:
    """Collects debugging context for errors."""
    
    def __init__(
        self,
        repo_root: Optional[Path] = None,
        collect_system_info: bool = True,
        collect_environment: bool = True,
        collect_call_stack: bool = True,
        collect_variables: bool = True,
        max_stack_frames: int = 20,
        max_variable_depth: int = 3
    ):
        """
        Initialize the error context collector.
        
        Args:
            repo_root: Repository root directory
            collect_system_info: Whether to collect system information
            collect_environment: Whether to collect environment variables
            collect_call_stack: Whether to collect call stack
            collect_variables: Whether to collect local variables
            max_stack_frames: Maximum number of stack frames to collect
            max_variable_depth: Maximum depth for variable inspection
        """
        self.repo_root = repo_root or Path.cwd()
        self.collect_system_info = collect_system_info
        self.collect_environment = collect_environment
        self.collect_call_stack = collect_call_stack
        self.collect_variables = collect_variables
        self.max_stack_frames = max_stack_frames
        self.max_variable_depth = max_variable_depth
        
        # Sensitive environment keys to exclude
        self.sensitive_keys = {
            "PASSWORD", "SECRET", "TOKEN", "KEY", "API_KEY", "PRIVATE_KEY",
            "CREDENTIAL", "AUTH", "SESSION", "COOKIE"
        }
    
    def collect(
        self,
        error: Exception,
        custom_context: Optional[Dict[str, Any]] = None,
        skip_frames: int = 0
    ) -> ErrorContext:
        """
        Collect error context.
        
        Args:
            error: The error that occurred
            custom_context: Additional custom context
            skip_frames: Number of stack frames to skip
            
        Returns:
            Collected error context
        """
        context = ErrorContext()
        context.timestamp = datetime.now().isoformat()
        
        if self.collect_system_info:
            context.system_info = self._collect_system_info()
        
        if self.collect_environment:
            context.environment = self._collect_environment()
        
        if self.collect_call_stack:
            context.call_stack = self._collect_call_stack(skip_frames)
        
        if self.collect_variables:
            context.variables = self._collect_variables()
        
        context.process_info = self._collect_process_info()
        context.files = self._collect_file_info()
        
        if custom_context:
            context.custom_context = custom_context
        
        return context
    
    def _collect_system_info(self) -> Dict[str, str]:
        """Collect system information."""
        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "hostname": platform.node(),
        }
    
    def _collect_environment(self) -> Dict[str, str]:
        """Collect environment variables (filtered)."""
        env_vars = {}
        
        for key, value in os.environ.items():
            # Skip sensitive keys
            if any(sensitive in key.upper() for sensitive in self.sensitive_keys):
                continue
            
            # Skip very long values
            if len(str(value)) > 500:
                value = f"{str(value)[:500]}... (truncated)"
            
            env_vars[key] = str(value)
        
        return env_vars
    
    def _collect_call_stack(self, skip_frames: int = 0) -> List[Dict[str, Any]]:
        """Collect call stack information."""
        frames = []
        
        # Get the current stack
        stack = inspect.stack()
        
        # Skip frames as requested
        start_frame = skip_frames + 1  # +1 for this method
        end_frame = min(start_frame + self.max_stack_frames, len(stack))
        
        for frame_info in stack[start_frame:end_frame]:
            frame = {
                "filename": frame_info.filename,
                "line_number": frame_info.lineno,
                "function": frame_info.function,
                "code_context": frame_info.code_context,
                "local_vars": self._sanitize_variables(frame_info.frame.f_locals)
            }
            frames.append(frame)
        
        return frames
    
    def _collect_variables(self) -> Dict[str, Any]:
        """Collect current variables from the calling frame."""
        try:
            # Get the frame that called this method
            frame = inspect.currentframe()
            if frame and frame.f_back:
                return self._sanitize_variables(frame.f_back.f_locals)
        except Exception:
            pass
        
        return {}
    
    def _sanitize_variables(
        self,
        variables: Dict[str, Any],
        depth: int = 0
    ) -> Dict[str, Any]:
        """
        Sanitize variables for logging (remove sensitive data).
        
        Args:
            variables: Variables to sanitize
            depth: Current recursion depth
            
        Returns:
            Sanitized variables
        """
        if depth >= self.max_variable_depth:
            return {"_depth_limit": "Reached maximum depth"}
        
        sanitized = {}
        
        for key, value in variables.items():
            # Skip private/internal variables
            if key.startswith("_"):
                continue
            
            # Skip special variables
            if key in ["self", "cls", "__class__"]:
                continue
            
            try:
                sanitized_value = self._sanitize_value(value, depth)
                sanitized[key] = sanitized_value
            except Exception:
                sanitized[key] = "<unable to serialize>"
        
        return sanitized
    
    def _sanitize_value(self, value: Any, depth: int) -> Any:
        """
        Sanitize a single value.
        
        Args:
            value: Value to sanitize
            depth: Current recursion depth
            
        Returns:
            Sanitized value
        """
        # Handle None
        if value is None:
            return None
        
        # Handle primitives
        if isinstance(value, (bool, int, float)):
            return value
        
        # Handle strings
        if isinstance(value, str):
            if len(value) > 200:
                return f"{value[:200]}... (truncated)"
            return value
        
        # Handle lists
        if isinstance(value, (list, tuple)):
            if depth >= self.max_variable_depth - 1:
                return f"<{type(value).__name__} with {len(value)} items>"
            return [self._sanitize_value(item, depth + 1) for item in value[:10]]
        
        # Handle dicts
        if isinstance(value, dict):
            if depth >= self.max_variable_depth - 1:
                return f"<dict with {len(value)} keys>"
            return {
                k: self._sanitize_value(v, depth + 1)
                for k, v in list(value.items())[:10]
            }
        
        # Handle objects
        if hasattr(value, "__dict__"):
            return f"<{type(value).__name__} object>"
        
        # Handle other types
        return f"<{type(value).__name__}>"
    
    def _collect_process_info(self) -> Dict[str, Any]:
        """Collect process information."""
        import psutil
        try:
            process = psutil.Process()
            return {
                "pid": process.pid,
                "ppid": process.ppid(),
                "name": process.name(),
                "username": process.username(),
                "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
                "status": process.status(),
                "cpu_percent": process.cpu_percent(),
                "memory_info": {
                    "rss": process.memory_info().rss,
                    "vms": process.memory_info().vms
                },
                "num_threads": process.num_threads(),
                "num_fds": process.num_fds() if hasattr(process, 'num_fds') else None
            }
        except (ImportError, Exception):
            # psutil not available or error collecting info
            return {
                "pid": os.getpid(),
                "ppid": os.getppid(),
                "uid": os.getuid(),
                "gid": os.getgid(),
            }
    
    def _collect_file_info(self) -> Dict[str, Dict[str, Any]]:
        """Collect information about relevant files."""
        files = {}
        
        # Add git info if available
        try:
            import subprocess
            
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )
            if result.returncode == 0:
                files["git_branch"] = {
                    "value": result.stdout.strip(),
                    "description": "Current git branch"
                }
            
            # Get latest commit
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )
            if result.returncode == 0:
                files["git_commit"] = {
                    "value": result.stdout.strip(),
                    "description": "Latest git commit"
                }
            
            # Get modified files
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                cwd=self.repo_root
            )
            if result.returncode == 0 and result.stdout.strip():
                modified_files = result.stdout.strip().split("\n")
                files["git_modified"] = {
                    "value": modified_files,
                    "count": len(modified_files),
                    "description": "Modified files in working directory"
                }
        except (FileNotFoundError, subprocess.SubprocessError):
            pass
        
        # Add repository info
        files["repository"] = {
            "path": str(self.repo_root),
            "exists": self.repo_root.exists(),
            "is_git_repo": (self.repo_root / ".git").exists()
        }
        
        return files


def collect_error_context(
    error: Exception,
    repo_root: Optional[Path] = None,
    custom_context: Optional[Dict[str, Any]] = None
) -> ErrorContext:
    """
    Collect error context.
    
    Args:
        error: The error that occurred
        repo_root: Repository root directory
        custom_context: Additional custom context
        
    Returns:
        Collected error context
    """
    collector = ErrorContextCollector(repo_root)
    return collector.collect(error, custom_context)


def with_error_context(
    collect_system_info: bool = True,
    collect_environment: bool = True,
    collect_variables: bool = True
) -> Callable:
    """
    Decorator to automatically collect error context.
    
    Args:
        collect_system_info: Whether to collect system information
        collect_environment: Whether to collect environment variables
        collect_variables: Whether to collect local variables
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Collect context
                context = collect_error_context(e, custom_context={
                    "function": func.__name__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                })
                
                # Add context to exception if it's an IFlowError
                if isinstance(e, IFlowError):
                    e.context = context.to_dict()
                
                raise
        
        return wrapper
    return decorator


class ErrorContextManager:
    """Context manager for collecting error context."""
    
    def __init__(
        self,
        repo_root: Optional[Path] = None,
        **collector_kwargs
    ):
        """
        Initialize the error context manager.
        
        Args:
            repo_root: Repository root directory
            **collector_kwargs: Additional arguments for ErrorContextCollector
        """
        self.repo_root = repo_root
        self.collector_kwargs = collector_kwargs
        self.collector: Optional[ErrorContextCollector] = None
    
    def __enter__(self):
        """Enter the context manager."""
        self.collector = ErrorContextCollector(self.repo_root, **self.collector_kwargs)
        return self.collector
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        if exc_type is not None and self.collector:
            # Collect context for the exception
            context = self.collector.collect(exc_val)
            
            # Add context to exception if it's an IFlowError
            if isinstance(exc_val, IFlowError):
                exc_val.context = context.to_dict()
        
        return False  # Don't suppress exceptions


def error_context(repo_root: Optional[Path] = None, **kwargs) -> ErrorContextManager:
    """
    Create an error context manager.
    
    Args:
        repo_root: Repository root directory
        **kwargs: Additional arguments for ErrorContextCollector
        
    Returns:
        ErrorContextManager instance
    """
    return ErrorContextManager(repo_root, **kwargs)