"""Error Translator - Translates technical errors to user-friendly messages.

This module provides functionality for translating technical error messages
into user-friendly, actionable messages that non-technical users can understand.
"""

from typing import Any, Dict, Optional
from enum import Enum

from .exceptions import IFlowError, ErrorCode


class Audience(Enum):
    """Target audience for error messages."""
    END_USER = "end_user"
    DEVELOPER = "developer"
    ADMINISTRATOR = "administrator"
    SUPPORT = "support"


class ErrorTranslator:
    """Translates technical errors to user-friendly messages."""
    
    # User-friendly message templates
    USER_FRIENDLY_MESSAGES = {
        ErrorCode.GIT_ERROR: {
            Audience.END_USER: (
                "We encountered an issue with Git. "
                "This usually happens when there's a problem with version control. "
                "Please try again, or contact your team's developer if this persists."
            ),
            Audience.DEVELOPER: (
                "Git operation failed: {operation}. "
                "Check git status and ensure you have the correct branch checked out. "
                "Verify git is properly configured and you have the necessary permissions."
            ),
            Audience.ADMINISTRATOR: (
                "Git operation failure detected. "
                "Check repository access permissions and git configuration. "
                "Verify the git server is accessible and responsive."
            ),
            Audience.SUPPORT: (
                "Git error: {operation} - {details}. "
                "Review git configuration and repository state. "
                "Check for network issues or permission problems."
            )
        },
        ErrorCode.FILE_NOT_FOUND: {
            Audience.END_USER: (
                "We couldn't find the file you're looking for. "
                "Please check the file name and try again, or ask your team for help."
            ),
            Audience.DEVELOPER: (
                "File not found: {file_path}. "
                "Verify the file exists and the path is correct. "
                "Check if you're in the right directory."
            ),
            Audience.ADMINISTRATOR: (
                "File access failure: {file_path}. "
                "Verify file exists and user has read permissions. "
                "Check file system integrity."
            ),
            Audience.SUPPORT: (
                "File not found error: {file_path}. "
                "Details: {details}. "
                "Check file system and permissions."
            )
        },
        ErrorCode.FILE_READ_ERROR: {
            Audience.END_USER: (
                "We had trouble reading a file. "
                "This might be a temporary issue. Please try again or contact support."
            ),
            Audience.DEVELOPER: (
                "Failed to read file: {file_path}. "
                "Check file permissions and ensure it's not locked. "
                "Verify the file is not corrupted."
            ),
            Audience.ADMINISTRATOR: (
                "File read access denied: {file_path}. "
                "Check user permissions and file locks. "
                "Verify file system integrity."
            ),
            Audience.SUPPORT: (
                "File read error: {file_path}. "
                "Details: {details}. "
                "Check permissions and file locks."
            )
        },
        ErrorCode.FILE_WRITE_ERROR: {
            Audience.END_USER: (
                "We couldn't save a file. "
                "This might be due to permissions or disk space. Please try again or contact support."
            ),
            Audience.DEVELOPER: (
                "Failed to write file: {file_path}. "
                "Check write permissions and available disk space. "
                "Ensure the directory exists and is writable."
            ),
            Audience.ADMINISTRATOR: (
                "File write access denied: {file_path}. "
                "Check user write permissions and disk space. "
                "Verify directory exists and is writable."
            ),
            Audience.SUPPORT: (
                "File write error: {file_path}. "
                "Details: {details}. "
                "Check permissions and disk space."
            )
        },
        ErrorCode.VALIDATION_ERROR: {
            Audience.END_USER: (
                "Some information you provided doesn't look right. "
                "Please check your input and try again, or ask your team for help."
            ),
            Audience.DEVELOPER: (
                "Validation failed: {field}. "
                "Check the value format and ensure it meets requirements. "
                "Review the schema documentation for valid values."
            ),
            Audience.ADMINISTRATOR: (
                "Input validation failure: {field}. "
                "Review validation rules and ensure data format is correct. "
                "Check for malformed input."
            ),
            Audience.SUPPORT: (
                "Validation error: {field}. "
                "Details: {details}. "
                "Review input format and validation rules."
            )
        },
        ErrorCode.NOT_FOUND: {
            Audience.END_USER: (
                "We couldn't find what you're looking for. "
                "Please check the name or contact your team for help."
            ),
            Audience.DEVELOPER: (
                "Resource not found: {resource}. "
                "Verify the resource name and check if it exists. "
                "Ensure you have the correct permissions."
            ),
            Audience.ADMINISTRATOR: (
                "Resource access failure: {resource}. "
                "Check if resource exists and user has access. "
                "Verify resource permissions."
            ),
            Audience.SUPPORT: (
                "Resource not found: {resource}. "
                "Details: {details}. "
                "Check resource existence and permissions."
            )
        },
        ErrorCode.ALREADY_EXISTS: {
            Audience.END_USER: (
                "This already exists. "
                "You can use the existing one, or choose a different name."
            ),
            Audience.DEVELOPER: (
                "Resource already exists: {resource}. "
                "Use the existing resource or delete it first. "
                "Choose a different name if needed."
            ),
            Audience.ADMINISTRATOR: (
                "Duplicate resource detected: {resource}. "
                "Verify if this is intentional. "
                "Review existing resources before creating new ones."
            ),
            Audience.SUPPORT: (
                "Resource already exists: {resource}. "
                "Details: {details}. "
                "Check if this is intentional."
            )
        },
        ErrorCode.PERMISSION_DENIED: {
            Audience.END_USER: (
                "You don't have permission to do this. "
                "Please contact your administrator or team lead for access."
            ),
            Audience.DEVELOPER: (
                "Permission denied: {operation}. "
                "Check your user permissions and authentication. "
                "Ensure you're logged in with the correct account."
            ),
            Audience.ADMINISTRATOR: (
                "Access denied: {operation}. "
                "Review user permissions and roles. "
                "Check authentication status and account settings."
            ),
            Audience.SUPPORT: (
                "Permission denied: {operation}. "
                "Details: {details}. "
                "Review user permissions and authentication."
            )
        },
        ErrorCode.TIMEOUT: {
            Audience.END_USER: (
                "This is taking longer than expected. "
                "Please try again, or contact support if the problem continues."
            ),
            Audience.DEVELOPER: (
                "Operation timed out: {operation}. "
                "Increase the timeout or optimize the operation. "
                "Check for network issues or performance problems."
            ),
            Audience.ADMINISTRATOR: (
                "Operation timeout: {operation}. "
                "Review timeout settings and system performance. "
                "Check for network or resource constraints."
            ),
            Audience.SUPPORT: (
                "Timeout error: {operation}. "
                "Timeout: {timeout} seconds. "
                "Details: {details}. "
                "Check system performance and network."
            )
        },
        ErrorCode.CIRCULAR_DEPENDENCY: {
            Audience.END_USER: (
                "There's a problem with how things are connected. "
                "Please contact your team's developer to help fix this."
            ),
            Audience.DEVELOPER: (
                "Circular dependency detected: {cycle}. "
                "Review the dependency graph and remove circular references. "
                "Restructure to be acyclic."
            ),
            Audience.ADMINISTRATOR: (
                "Dependency cycle detected: {cycle}. "
                "Review project structure and dependencies. "
                "Ensure dependencies form a DAG (Directed Acyclic Graph)."
            ),
            Audience.SUPPORT: (
                "Circular dependency: {cycle}. "
                "Details: {details}. "
                "Review and restructure dependencies."
            )
        },
        ErrorCode.INVALID_STATE: {
            Audience.END_USER: (
                "Something is out of order. "
                "Please complete the previous steps first, or contact support for help."
            ),
            Audience.DEVELOPER: (
                "Invalid state for operation: {operation}. "
                "Current state: {current_state}, Required: {required_state}. "
                "Complete prerequisite operations first."
            ),
            Audience.ADMINISTRATOR: (
                "State transition error: {operation}. "
                "Review workflow state and required prerequisites. "
                "Ensure operations are performed in correct order."
            ),
            Audience.SUPPORT: (
                "Invalid state error: {operation}. "
                "Details: {details}. "
                "Review workflow state and prerequisites."
            )
        },
        ErrorCode.DEPENDENCY_ERROR: {
            Audience.END_USER: (
                "Something needed for this to work is missing. "
                "Please contact your team's developer to help install it."
            ),
            Audience.DEVELOPER: (
                "Dependency error: {dependency}. "
                "Install or update the missing dependency. "
                "Check package manager and version requirements."
            ),
            Audience.ADMINISTRATOR: (
                "Dependency failure: {dependency}. "
                "Review dependency installation and configuration. "
                "Ensure all required packages are available."
            ),
            Audience.SUPPORT: (
                "Dependency error: {dependency}. "
                "Details: {details}. "
                "Install or update dependencies."
            )
        },
        ErrorCode.CONFIGURATION_ERROR: {
            Audience.END_USER: (
                "There's a problem with the settings. "
                "Please contact your team's developer or administrator to fix this."
            ),
            Audience.DEVELOPER: (
                "Configuration error: {config_key}. "
                "Check the configuration file and format. "
                "Review documentation for valid options."
            ),
            Audience.ADMINISTRATOR: (
                "Configuration failure: {config_key}. "
                "Review configuration settings and format. "
                "Check for invalid or missing values."
            ),
            Audience.SUPPORT: (
                "Configuration error: {config_key}. "
                "Details: {details}. "
                "Review configuration file."
            )
        },
        ErrorCode.SECURITY_ERROR: {
            Audience.END_USER: (
                "We detected a security concern. "
                "Please contact your security team or administrator immediately."
            ),
            Audience.DEVELOPER: (
                "Security error: {security_issue}. "
                "Review the security settings and code. "
                "Ensure proper authentication and authorization."
            ),
            Audience.ADMINISTRATOR: (
                "Security violation: {security_issue}. "
                "Review security policies and access controls. "
                "Contact security team if needed."
            ),
            Audience.SUPPORT: (
                "Security error: {security_issue}. "
                "Details: {details}. "
                "Review security settings."
            )
        },
        ErrorCode.BACKUP_ERROR: {
            Audience.END_USER: (
                "We had trouble creating a backup. "
                "This might be a temporary issue. Please try again or contact support."
            ),
            Audience.DEVELOPER: (
                "Backup operation failed: {operation}. "
                "Check disk space and backup directory permissions. "
                "Ensure backup location is accessible."
            ),
            Audience.ADMINISTRATOR: (
                "Backup failure: {operation}. "
                "Review backup configuration and storage. "
                "Check disk space and permissions."
            ),
            Audience.SUPPORT: (
                "Backup error: {operation}. "
                "Details: {details}. "
                "Check backup configuration and storage."
            )
        },
        ErrorCode.VERSION_ERROR: {
            Audience.END_USER: (
                "There's a version compatibility issue. "
                "Please contact your team's developer to help update to a compatible version."
            ),
            Audience.DEVELOPER: (
                "Version error: {version_info}. "
                "Check version format and compatibility requirements. "
                "Update to a compatible version."
            ),
            Audience.ADMINISTRATOR: (
                "Version compatibility issue: {version_info}. "
                "Review version requirements and update policies. "
                "Ensure all components are compatible."
            ),
            Audience.SUPPORT: (
                "Version error: {version_info}. "
                "Details: {details}. "
                "Review version compatibility."
            )
        }
    }
    
    def __init__(
        self,
        default_audience: Audience = Audience.END_USER,
        include_context: bool = False
    ):
        """
        Initialize the error translator.
        
        Args:
            default_audience: Default target audience
            include_context: Whether to include technical context
        """
        self.default_audience = default_audience
        self.include_context = include_context
    
    def translate(
        self,
        error: IFlowError,
        audience: Optional[Audience] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Translate an error to a user-friendly message.
        
        Args:
            error: The error to translate
            audience: Target audience (uses default if None)
            context: Additional context for template formatting
            
        Returns:
            User-friendly error message
        """
        audience = audience or self.default_audience
        
        # Get the template
        templates = self.USER_FRIENDLY_MESSAGES.get(error.code)
        if not templates:
            return self._fallback_message(error, audience)
        
        template = templates.get(audience)
        if not template:
            template = templates.get(Audience.END_USER, self._fallback_message(error, audience))
        
        # Format template with context
        message = self._format_template(template, context or {})
        
        # Add context if requested
        if self.include_context and audience in [Audience.DEVELOPER, Audience.ADMINISTRATOR, Audience.SUPPORT]:
            message = self._add_context(message, error, context or {})
        
        return message
    
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
    
    def _add_context(
        self,
        message: str,
        error: IFlowError,
        context: Dict[str, Any]
    ) -> str:
        """
        Add technical context to the message.
        
        Args:
            message: Original message
            error: The error
            context: Additional context
            
        Returns:
            Message with added context
        """
        lines = [message]
        lines.append("")
        lines.append("Technical Details:")
        lines.append("-" * 30)
        lines.append(f"Error Code: {error.code.name} ({error.code.value})")
        lines.append(f"Category: {error.category.value}")
        
        if context:
            for key, value in context.items():
                lines.append(f"{key}: {value}")
        
        return "\n".join(lines)
    
    def _fallback_message(
        self,
        error: IFlowError,
        audience: Audience
    ) -> str:
        """
        Generate a fallback message when no template is found.
        
        Args:
            error: The error
            audience: Target audience
            
        Returns:
            Fallback message
        """
        if audience == Audience.END_USER:
            return (
                "We encountered an unexpected error. "
                "Please try again or contact support if the problem continues."
            )
        elif audience == Audience.DEVELOPER:
            return f"Error: {error.code.name} - {str(error)}"
        elif audience == Audience.ADMINISTRATOR:
            return f"System error: {error.code.name} - Category: {error.category.value}"
        else:  # SUPPORT
            return f"Error: {error.code.name} ({error.code.value}) - {str(error)}"
    
    def translate_for_support(
        self,
        error: IFlowError,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Translate an error for support personnel.
        
        Args:
            error: The error to translate
            context: Additional context
            
        Returns:
            Support-oriented error message
        """
        return self.translate(error, Audience.SUPPORT, context)
    
    def translate_for_user(
        self,
        error: IFlowError,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Translate an error for end users.
        
        Args:
            error: The error to translate
            context: Additional context
            
        Returns:
            User-friendly error message
        """
        return self.translate(error, Audience.END_USER, context)
    
    def translate_for_developer(
        self,
        error: IFlowError,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Translate an error for developers.
        
        Args:
            error: The error to translate
            context: Additional context
            
        Returns:
        """
        return self.translate(error, Audience.DEVELOPER, context)


def translate_error(
    error: IFlowError,
    audience: Optional[Audience] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Translate an error to a user-friendly message.
    
    Args:
        error: The error to translate
        audience: Target audience
        context: Additional context
        
    Returns:
        User-friendly error message
    """
    translator = ErrorTranslator()
    return translator.translate(error, audience, context)


def translate_for_user(
    error: IFlowError,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Translate an error for end users.
    
    Args:
        error: The error to translate
        context: Additional context
        
    Returns:
        User-friendly error message
    """
    translator = ErrorTranslator()
    return translator.translate_for_user(error, context)
