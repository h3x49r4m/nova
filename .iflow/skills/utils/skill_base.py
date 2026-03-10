"""Skill Base Class.

This module provides a base class for all skill implementations,
extracting common patterns and providing standardized functionality.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add utils to path
utils_path = Path(__file__).parent
sys.path.insert(0, str(utils_path))

from .exceptions import IFlowError, ErrorCode, ValidationError
from .structured_logger import StructuredLogger, LogFormat
from .skill_config_schema import SkillConfigValidator
from .state_contract_validator import StateContractValidator


class SkillBase:
    """
    Base class for all skill implementations.
    
    Provides common functionality including:
    - Configuration loading and validation
    - Logging setup
    - State contract validation
    - Standard error handling
    - Git operations
    """
    
    def __init__(
        self,
        skill_name: str,
        repo_root: Optional[Path] = None,
        config_schema: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the skill base.
        
        Args:
            skill_name: Name of the skill (e.g., 'software-engineer')
            repo_root: Root directory of the repository (defaults to cwd)
            config_schema: Optional custom config schema (uses unified schema if None)
        """
        self.skill_name = skill_name
        self.repo_root = repo_root or Path.cwd()
        
        # Set up paths
        self.skill_dir = self.repo_root / '.iflow' / 'skills' / skill_name
        self.config_dir = self.skill_dir
        self.config_file = self.config_dir / 'config.json'
        self.state_dir = self.repo_root / '.state'
        self.logs_dir = self.repo_root / '.iflow' / 'logs'
        
        # Set up logger
        self.logger = StructuredLogger(
            name=skill_name,
            log_dir=self.logs_dir,
            log_format=LogFormat.JSON
        )
        
        # Set up config validator (before load_config)
        self.config_validator = SkillConfigValidator()
        
        # Load configuration
        self.config: Dict[str, Any] = {}
        self.load_config()
        
        # Set up state contract validator
        self.state_contract_validator = StateContractValidator(
            skill_dir=self.skill_dir,
            logger=self.logger
        )
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration for the skill.
        
        Override this method in subclasses to provide skill-specific defaults.
        
        Returns:
            Dictionary of default configuration values
        """
        return {
            'version': '1.0.0',
            'auto_commit': True
        }
    
    def load_config(self) -> None:
        """
        Load configuration from config file.
        
        Loads configuration from the config.json file, merging with defaults.
        Logs warnings if config file is invalid.
        """
        self.config = self.get_default_config()
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                
                # Validate config
                is_valid, errors = self.config_validator.validate(user_config)
                if not is_valid:
                    self.logger.warning(
                        f"Config validation failed: {', '.join(errors)}. Using defaults."
                    )
                else:
                    self.config.update(user_config)
                    self.logger.info(f"Configuration loaded from {self.config_file}")
            
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Failed to load config: {e}. Using defaults.")
        else:
            self.logger.info(f"No config file found at {self.config_file}. Using defaults.")
    
    def save_config(self) -> Tuple[int, str]:
        """
        Save current configuration to config file.
        
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Validate before saving
            is_valid, errors = self.config_validator.validate(self.config)
            if not is_valid:
                return 1, f"Config validation failed: {', '.join(errors)}"
            
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Save config
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            self.logger.info(f"Configuration saved to {self.config_file}")
            return 0, f"Configuration saved to {self.config_file}"
        
        except (IOError, OSError) as e:
            error_msg = f"Failed to save config: {e}"
            self.logger.error(error_msg)
            return 1, error_msg
    
    def get_state_dir(self, project_path: Optional[Path] = None) -> Path:
        """
        Get the state directory for a project.
        
        Args:
            project_path: Path to the project (defaults to repo_root)
            
        Returns:
            Path to the state directory
        """
        project_path = project_path or self.repo_root
        
        # Check for .iflow/skills/.shared-state/ (preferred)
        shared_state = project_path / '.iflow' / 'skills' / '.shared-state'
        if shared_state.exists():
            return shared_state
        
        # Check for .state/ (legacy support)
        state_dir = project_path / '.state'
        if state_dir.exists():
            return state_dir
        
        # Default to .iflow/skills/.shared-state/
        return shared_state
    
    def read_state_file(
        self,
        filename: str,
        project_path: Optional[Path] = None
    ) -> Tuple[int, str]:
        """
        Read a state file.
        
        Args:
            filename: Name of the state file (e.g., 'architecture-spec.md')
            project_path: Path to the project (defaults to repo_root)
            
        Returns:
            Tuple of (exit_code, content or error message)
        """
        state_dir = self.get_state_dir(project_path)
        state_file = state_dir / filename
        
        try:
            if not state_file.exists():
                error_msg = f"State file not found: {state_file}"
                self.logger.error(error_msg)
                return ErrorCode.FILE_NOT_FOUND.value, error_msg
            
            with open(state_file, 'r') as f:
                content = f.read()
            
            self.logger.debug(f"Read state file: {filename}")
            return 0, content
        
        except (IOError, OSError) as e:
            error_msg = f"Failed to read state file {filename}: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_READ_ERROR.value, error_msg
    
    def write_state_file(
        self,
        filename: str,
        content: str,
        project_path: Optional[Path] = None
    ) -> Tuple[int, str]:
        """
        Write a state file.
        
        Args:
            filename: Name of the state file (e.g., 'implementation.md')
            content: Content to write
            project_path: Path to the project (defaults to repo_root)
            
        Returns:
            Tuple of (exit_code, message)
        """
        state_dir = self.get_state_dir(project_path)
        state_file = state_dir / filename
        
        try:
            # Ensure state directory exists
            state_dir.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(state_file, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Wrote state file: {filename}")
            return 0, f"State file written: {state_file}"
        
        except (IOError, OSError) as e:
            error_msg = f"Failed to write state file {filename}: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def validate_state_contracts(
        self,
        project_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Validate all state contracts for the skill.
        
        Args:
            project_path: Path to the project (defaults to repo_root)
            
        Returns:
            Dictionary with validation results
        """
        project_path = project_path or self.repo_root
        return self.state_contract_validator.validate_all_contracts(project_path)
    
    def get_state_contracts(self) -> Dict[str, List[str]]:
        """
        Get all state contracts for the skill.
        
        Returns:
            Dictionary with 'read' and 'write' contract lists
        """
        return self.state_contract_validator.get_contracts()
    
    def log_workflow_start(self, workflow_name: str, **kwargs):
        """
        Log the start of a workflow.
        
        Args:
            workflow_name: Name of the workflow
            **kwargs: Additional context to log
        """
        self.logger.info(
            f"Starting workflow: {workflow_name}",
            extra={'workflow': workflow_name, **kwargs}
        )
    
    def log_workflow_complete(self, workflow_name: str, duration: float, **kwargs):
        """
        Log the completion of a workflow.
        
        Args:
            workflow_name: Name of the workflow
            duration: Duration in seconds
            **kwargs: Additional context to log
        """
        self.logger.info(
            f"Completed workflow: {workflow_name}",
            extra={'workflow': workflow_name, 'duration': duration, **kwargs}
        )
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """
        Log an error with context.
        
        Args:
            error: Exception to log
            context: Optional context dictionary
        """
        self.logger.error(
            f"Error: {str(error)}",
            extra={
                'error_type': type(error).__name__,
                'context': context or {}
            }
        )
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, str]:
        """
        Handle an error with standardized logging and response.
        
        Args:
            error: Exception to handle
            context: Optional context dictionary
            
        Returns:
            Tuple of (exit_code, error_message)
        """
        self.log_error(error, context)
        
        if isinstance(error, IFlowError):
            return error.code.value, str(error)
        elif isinstance(error, ValidationError):
            return ErrorCode.VALIDATION_ERROR.value, str(error)
        else:
            return ErrorCode.UNKNOWN_ERROR.value, str(error)
    
    def run_workflow(
        self,
        project_path: Path,
        workflow_name: str,
        **kwargs
    ) -> Tuple[int, str]:
        """
        Main workflow entry point.
        
        Override this method in subclasses to implement the skill's workflow.
        
        Args:
            project_path: Path to the project directory
            workflow_name: Name of the workflow to run
            **kwargs: Additional workflow parameters
            
        Returns:
            Tuple of (exit_code, message)
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.run_workflow() must be implemented"
        )
    
    def __repr__(self) -> str:
        """String representation of the skill."""
        return f"{self.__class__.__name__}(skill_name='{self.skill_name}', repo_root='{self.repo_root}')"