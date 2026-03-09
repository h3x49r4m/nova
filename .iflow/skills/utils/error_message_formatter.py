"""Error Message Formatter - Formats error messages with context and suggestions.

This module provides functionality for formatting error messages with
detailed context, suggestions, and actionable information.
"""

import traceback
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from .exceptions import ErrorCode, ErrorCategory


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorMessageFormatter:
    """Formats error messages with context and suggestions."""
    
    # Error templates with placeholders
    ERROR_TEMPLATES = {
        ErrorCode.GIT_ERROR: (
            "Git operation failed: {operation}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Check if git is installed and accessible\n"
            "- Verify you have the necessary permissions\n"
            "- Ensure the repository exists and is accessible\n"
            "- Try running the operation manually: git {command}"
        ),
        ErrorCode.FILE_NOT_FOUND: (
            "File not found: {file_path}\n"
            "\nSuggestions:\n"
            "- Check if the file path is correct\n"
            "- Verify the file exists in the repository\n"
            "- Ensure you're in the correct directory\n"
            "- Try using absolute path instead of relative"
        ),
        ErrorCode.FILE_READ_ERROR: (
            "Failed to read file: {file_path}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Check file permissions\n"
            "- Verify the file is not corrupted\n"
            "- Ensure the file is not locked by another process\n"
            "- Try opening the file manually"
        ),
        ErrorCode.FILE_WRITE_ERROR: (
            "Failed to write file: {file_path}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Check if you have write permissions\n"
            "- Verify the directory exists\n"
            "- Ensure sufficient disk space\n"
            "- Check if the file is locked by another process"
        ),
        ErrorCode.VALIDATION_ERROR: (
            "Validation failed: {field}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Check the value format\n"
            "- Verify against the schema requirements\n"
            "- Review the documentation for valid values\n"
            "- Ensure all required fields are provided"
        ),
        ErrorCode.NOT_FOUND: (
            "Resource not found: {resource}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Verify the resource name is correct\n"
            "- Check if the resource exists\n"
            "- Ensure you have access to the resource\n"
            "- Try listing available resources"
        ),
        ErrorCode.ALREADY_EXISTS: (
            "Resource already exists: {resource}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Use a different name\n"
            "- Delete the existing resource if no longer needed\n"
            "- Update the existing resource instead of creating new"
        ),
        ErrorCode.PERMISSION_DENIED: (
            "Permission denied: {operation}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Check your user permissions\n"
            "- Verify you're authenticated correctly\n"
            "- Contact your administrator for access\n"
            "- Ensure the resource allows the requested operation"
        ),
        ErrorCode.TIMEOUT: (
            "Operation timed out: {operation}\n"
            "Timeout: {timeout} seconds\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Increase the timeout duration\n"
            "- Check network connectivity\n"
            "- Verify the operation is expected to complete\n"
            "- Try running the operation during off-peak hours"
        ),
        ErrorCode.CIRCULAR_DEPENDENCY: (
            "Circular dependency detected: {cycle}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Review the dependency graph\n"
            "- Remove one of the circular references\n"
            "- Restructure the dependencies to be acyclic\n"
            "- Use a different approach that doesn't require circular dependencies"
        ),
        ErrorCode.INVALID_STATE: (
            "Invalid state for operation: {operation}\n"
            "Current state: {current_state}\n"
            "Required state: {required_state}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Complete prerequisite operations first\n"
            "- Reset the workflow if needed\n"
            "- Check the workflow status\n"
            "- Ensure you're following the correct sequence"
        ),
        ErrorCode.DEPENDENCY_ERROR: (
            "Dependency error: {dependency}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Install the missing dependency\n"
            "- Update to a compatible version\n"
            "- Check if the dependency is available\n"
            "- Review the dependency requirements"
        ),
        ErrorCode.CONFIGURATION_ERROR: (
            "Configuration error: {config_key}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Check the configuration file\n"
            "- Verify the configuration format\n"
            "- Review the documentation for valid options\n"
            "- Use default configuration if available"
        ),
        ErrorCode.SECURITY_ERROR: (
            "Security error: {security_issue}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Review the security settings\n"
            "- Ensure proper authentication\n"
            "- Check for malicious content\n"
            "- Contact security team if needed"
        ),
        ErrorCode.BACKUP_ERROR: (
            "Backup operation failed: {operation}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Check available disk space\n"
            "- Verify backup directory permissions\n"
            "- Ensure backup location is accessible\n"
            "- Try the operation again"
        ),
        ErrorCode.VERSION_ERROR: (
            "Version error: {version_info}\n"
            "Details: {details}\n"
            "\nSuggestions:\n"
            "- Check the version format\n"
            "- Verify version compatibility\n"
            "- Update to a compatible version\n"
            "- Review version requirements"
        ),
    }
    
    def __init__(
        self,
        include_traceback: bool = False,
        include_context: bool = True,
        include_suggestions: bool = True,
        max_context_lines: int = 3
    ):
        """
        Initialize the error message formatter.
        
        Args:
            include_traceback: Whether to include stack traces
            include_context: Whether to include context information
            include_suggestions: Whether to include suggestions
            max_context_lines: Maximum number of context lines to show
        """
        self.include_traceback = include_traceback
        self.include_context = include_context
        self.include_suggestions = include_suggestions
        self.max_context_lines = max_context_lines
    
    def format_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format an error with context and suggestions.
        
        Args:
            error: The exception to format
            context: Additional context information
            
        Returns:
            Formatted error message
        """
        # Get error details
        error_type = type(error).__name__
        error_message = str(error)
        error_code = getattr(error, 'code', None)
        error_category = getattr(error, 'category', None)
        
        # Build the error message
        lines = []
        
        # Error header
        lines.append(f"❌ {error_type}")
        lines.append("=" * 50)
        lines.append("")
        
        # Error message
        lines.append(f"Message: {error_message}")
        
        # Error code and category
        if error_code:
            lines.append(f"Error Code: {error_code.name} ({error_code.value})")
        
        if error_category:
            lines.append(f"Category: {error_category.value}")
        
        lines.append("")
        
        # Add context information
        if self.include_context and context:
            lines.append("Context:")
            lines.append("-" * 30)
            for key, value in context.items():
                lines.append(f"  {key}: {value}")
            lines.append("")
        
        # Add template-based suggestions
        if self.include_suggestions and error_code:
            template = self.ERROR_TEMPLATES.get(error_code)
            if template:
                # Format template with context
                formatted = self._format_template(template, context or {})
                lines.append("Suggestions:")
                lines.append("-" * 30)
                lines.append(formatted)
                lines.append("")
        
        # Add traceback
        if self.include_traceback:
            lines.append("Stack Trace:")
            lines.append("-" * 30)
            tb_lines = traceback.format_exc().split("\n")
            lines.extend(tb_lines[:self.max_context_lines + 2])
            lines.append("")
        
        # Add recovery information
        lines.append("Recovery:")
        lines.append("-" * 30)
        lines.append("  - Review the error details above")
        lines.append("  - Fix the underlying issue")
        lines.append("  - Retry the operation")
        lines.append("  - Contact support if the issue persists")
        
        return "\n".join(lines)
    
    def _format_template(self, template: str, context: Dict[str, Any]) -> str:
        """
        Format a template with context values.
        
        Args:
            template: Template string with placeholders
            context: Context values
            
        Returns:
            Formatted template
        """
        try:
            return template.format(**context)
        except KeyError:
            # Missing placeholder, return template as-is
            return template
    
    def format_error_summary(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format a brief error summary.
        
        Args:
            error: The exception to format
            context: Additional context information
            
        Returns:
            Brief error summary
        """
        error_type = type(error).__name__
        error_message = str(error)
        error_code = getattr(error, 'code', None)
        
        parts = [error_type]
        
        if error_code:
            parts.append(f"[{error_code.name}]")
        
        parts.append(f": {error_message}")
        
        return " ".join(parts)
    
    def format_error_json(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format an error as a JSON-compatible dictionary.
        
        Args:
            error: The exception to format
            context: Additional context information
            
        Returns:
            Dictionary with error information
        """
        
        error_data = {
            "error": type(error).__name__,
            "message": str(error),
            "code": getattr(error, 'code', None),
            "category": getattr(error, 'category', None),
        }
        
        if context:
            error_data["context"] = context
        
        if self.include_traceback:
            error_data["traceback"] = traceback.format_exc()
        
        if self.include_suggestions and getattr(error, 'code', None):
            template = self.ERROR_TEMPLATES.get(error.code)
            if template:
                error_data["suggestions"] = self._format_template(
                    template,
                    context or {}
                )
        
        return error_data
    
    def format_multiple_errors(
        self,
        errors: List[Tuple[Exception, Optional[Dict[str, Any]]]]
    ) -> str:
        """
        Format multiple errors.
        
        Args:
            errors: List of (error, context) tuples
            
        Returns:
            Formatted multi-error message
        """
        lines = []
        lines.append(f"❌ {len(errors)} Error(s) Detected")
        lines.append("=" * 50)
        lines.append("")
        
        for i, (error, context) in enumerate(errors, 1):
            lines.append(f"Error #{i}:")
            lines.append("-" * 30)
            lines.append(self.format_error(error, context))
            lines.append("")
        
        return "\n".join(lines)
    
    def get_severity(
        self,
        error: Exception
    ) -> ErrorSeverity:
        """
        Determine the severity of an error.
        
        Args:
            error: The exception to evaluate
            
        Returns:
            Error severity level
        """
        error_code = getattr(error, 'code', None)
        error_category = getattr(error, 'category', None)
        
        # Critical errors
        if error_code in [
            ErrorCode.SECURITY_ERROR,
            ErrorCode.VERSION_ERROR
        ]:
            return ErrorSeverity.CRITICAL
        
        if error_category == ErrorCategory.SYSTEM_ERROR:
            return ErrorSeverity.CRITICAL
        
        # Regular errors
        if error_code or error_category == ErrorCategory.PERMANENT:
            return ErrorSeverity.ERROR
        
        # Warnings
        if error_category == ErrorCategory.TRANSIENT:
            return ErrorSeverity.WARNING
        
        # Default
        return ErrorSeverity.ERROR
    
    def format_for_log(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Format an error for logging.
        
        Args:
            error: The exception to format
            context: Additional context information
            
        Returns:
            Dictionary suitable for structured logging
        """
        severity = self.get_severity(error)
        error_code = getattr(error, 'code', None)
        error_category = getattr(error, 'category', None)
        
        return {
            "severity": severity.value,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_code": error_code.name if error_code else None,
            "error_category": error_category.value if error_category else None,
            "context": context or {},
            "traceback": traceback.format_exc() if self.include_traceback else None
        }


def format_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    include_traceback: bool = False
) -> str:
    """
    Format an error with context and suggestions.
    
    Args:
        error: The exception to format
        context: Additional context information
        include_traceback: Whether to include stack traces
        
    Returns:
        Formatted error message
    """
    formatter = ErrorMessageFormatter(include_traceback=include_traceback)
    return formatter.format_error(error, context)


def create_error_context(
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Create an error context dictionary.
    
    Args:
        **kwargs: Context key-value pairs
        
    Returns:
        Context dictionary
    """
    return kwargs