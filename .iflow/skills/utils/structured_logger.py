"""Structured Logger - Provides centralized logging with levels and filtering.

This module provides a comprehensive logging system with structured output,
log levels, filtering capabilities, and rotation support.
"""

import json
import logging
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import threading
from logging.handlers import RotatingFileHandler

try:
    from .exceptions import IFlowError, ErrorCode
except ImportError:
    from exceptions import IFlowError, ErrorCode


class LogLevel(Enum):
    """Log levels."""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogFormat(Enum):
    """Log format types."""
    JSON = "json"
    TEXT = "text"
    CONCISE = "concise"


class StructuredLogger:
    """Structured logger with levels, filtering, and rotation."""
    
    _instance: Optional['StructuredLogger'] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one logger instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        name: str = "iflow",
        log_dir: Optional[Path] = None,
        log_level: LogLevel = LogLevel.INFO,
        log_format: LogFormat = LogFormat.JSON,
        enable_console: bool = True,
        enable_file: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        Initialize the structured logger.
        
        Args:
            name: Logger name
            log_dir: Directory for log files
            log_level: Minimum log level to capture
            log_format: Output format (json, text, concise)
            enable_console: Enable console output
            enable_file: Enable file output
            max_file_size: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
        """
        if self._initialized:
            return
        
        self.name = name
        self.log_dir = log_dir or Path(".iflow/logs")
        self.log_level = log_level
        self.log_format = log_format
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.filters: Dict[str, Set[str]] = {
            "include": set(),
            "exclude": set()
        }
        
        # Create log directory if it doesn't exist
        if enable_file:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level.value)
        self.logger.handlers.clear()
        
        # Setup handlers
        self._setup_handlers()
        
        self._initialized = True
    
    def _setup_handlers(self):
        """Setup console and file handlers."""
        formatter = self._get_formatter()
        
        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level.value)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # File handler with rotation
        if self.enable_file:
            log_file = self.log_dir / f"{self.name}.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=self.max_file_size,
                backupCount=self.backup_count
            )
            file_handler.setLevel(self.log_level.value)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def _get_formatter(self) -> logging.Formatter:
        """Get the appropriate formatter based on log format."""
        if self.log_format == LogFormat.JSON:
            return JSONFormatter()
        elif self.log_format == LogFormat.TEXT:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        else:  # CONCISE
            return logging.Formatter('%(levelname)s: %(message)s')
    
    def add_filter(self, filter_type: str, patterns: List[str]):
        """
        Add include/exclude filters.
        
        Args:
            filter_type: Either 'include' or 'exclude'
            patterns: List of patterns to match (wildcards supported)
        """
        if filter_type in self.filters:
            self.filters[filter_type].update(patterns)
    
    def _should_log(self, module: str) -> bool:
        """
        Check if a message should be logged based on filters.
        
        Args:
            module: Module name
            
        Returns:
            True if should log, False otherwise
        """
        # Check exclude filters
        for pattern in self.filters["exclude"]:
            if self._matches_pattern(module, pattern):
                return False
        
        # Check include filters (if any are defined)
        if self.filters["include"]:
            for pattern in self.filters["include"]:
                if self._matches_pattern(module, pattern):
                    return True
            return False
        
        return True
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches a wildcard pattern."""
        import fnmatch
        return fnmatch.fnmatch(text, pattern)
    
    def debug(self, message: str, **kwargs):
        """Log a debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log an info message."""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log a warning message."""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log an error message."""
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log a critical message."""
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    def _log(self, level: LogLevel, message: str, **kwargs):
        """
        Log a message with additional context.
        
        Args:
            level: Log level
            message: Message to log
            **kwargs: Additional context fields
        """
        # Extract module from kwargs or use caller's module
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            module = frame.f_back.f_globals.get('__name__', 'unknown')
        else:
            module = 'unknown'
        
        # Check filters
        if not self._should_log(module):
            return
        
        # Create log record with extra data
        extra = {
            'log_module': module,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        
        # Log at appropriate level
        log_func = {
            LogLevel.DEBUG: self.logger.debug,
            LogLevel.INFO: self.logger.info,
            LogLevel.WARNING: self.logger.warning,
            LogLevel.ERROR: self.logger.error,
            LogLevel.CRITICAL: self.logger.critical
        }.get(level, self.logger.info)
        
        log_func(message, extra=extra)
    
    def set_level(self, level: LogLevel):
        """Set the minimum log level."""
        self.log_level = level
        self.logger.setLevel(level.value)
        for handler in self.logger.handlers:
            handler.setLevel(level.value)
    
    def set_format(self, format: LogFormat):
        """Set the log format."""
        self.log_format = format
        formatter = self._get_formatter()
        for handler in self.logger.handlers:
            handler.setFormatter(formatter)


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON structured logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": getattr(record, 'timestamp', datetime.now().isoformat()),
            "level": record.levelname,
            "logger": record.name,
            "module": getattr(record, 'log_module', 'unknown'),
            "message": record.getMessage(),
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add stack trace if present
        if record.stack_info:
            log_data["stack_trace"] = self.formatStack(record.stack_info)
        
        # Add any extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'lineno', 
                          'funcName', 'created', 'msecs', 'relativeCreated',
                          'thread', 'threadName', 'processName', 'process',
                          'exc_info', 'exc_text', 'stack_info', 'message',
                          'asctime', 'timestamp']:
                if not key.startswith('_'):
                    log_data[key] = value
        
        return json.dumps(log_data)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> StructuredLogger:
        """Get or create a logger for this class."""
        if not hasattr(self, '_logger'):
            self._logger = StructuredLogger()
        return self._logger


def get_logger(
    name: str = "iflow",
    log_level: LogLevel = LogLevel.INFO,
    log_format: LogFormat = LogFormat.JSON
) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name
        log_level: Log level
        log_format: Log format
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(
        name=name,
        log_level=log_level,
        log_format=log_format
    )


def configure_logging(
    log_level: LogLevel = LogLevel.INFO,
    log_format: LogFormat = LogFormat.JSON,
    log_dir: Optional[Path] = None,
    enable_console: bool = True,
    enable_file: bool = True
):
    """
    Configure global logging settings.
    
    Args:
        log_level: Log level
        log_format: Log format
        log_dir: Directory for log files
        enable_console: Enable console output
        enable_file: Enable file output
    """
    StructuredLogger(
        name="iflow",
        log_dir=log_dir,
        log_level=log_level,
        log_format=log_format,
        enable_console=enable_console,
        enable_file=enable_file
    )