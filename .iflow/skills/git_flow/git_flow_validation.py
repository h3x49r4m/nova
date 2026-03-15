#!/usr/bin/env python3
"""
Git-Flow Validation Module
Handles validation and prerequisite checks for operations.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from utils import (
    run_git_command,
    StructuredLogger,
    LogFormat,
    LogLevel,
    validate_workflow_state,
    validate_branch_state,
    validate_workflow_prerequisites,
    InputSanitizer
)
from .git_flow_config import GitFlowConfig
from .git_flow_branches import GitFlowBranches


class GitFlowValidation:
    """Manages Git-Flow validation and prerequisite checks."""
    
    def __init__(self, config: GitFlowConfig, branches: GitFlowBranches):
        """
        Initialize validation manager.
        
        Args:
            config: GitFlowConfig instance
            branches: GitFlowBranches instance
        """
        self.config = config
        self.branches = branches
        self.logger = config.logger
        self.repo_root = config.repo_root
        self.input_sanitizer = InputSanitizer()
    
    def check_prerequisites(self, operation: str) -> Tuple[int, str]:
        """
        Check if prerequisites are met for an operation.
        
        Args:
            operation: Operation to check prerequisites for
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Validate operation name
            if not self.input_sanitizer.validate_string(operation):
                return (1, f"Invalid operation name: {operation}")
            
            # Check if repository is a git repository
            if not self._is_git_repository():
                return (1, "Not a git repository")
            
            # Check if working directory is clean
            if not self._is_working_directory_clean():
                return (1, "Working directory is not clean. Commit or stash changes first.")
            
            # Check if workflow state is valid
            if self.config.workflow_state:
                is_valid, msg = validate_workflow_state(self.config.workflow_state.to_dict())
                if not is_valid:
                    return (1, f"Invalid workflow state: {msg}")
            
            # Check if branch states are valid
            for branch_name, branch_state in self.config.branch_states.items():
                is_valid, msg = validate_branch_state(branch_state.to_dict())
                if not is_valid:
                    return (1, f"Invalid branch state for '{branch_name}': {msg}")
            
            # Check workflow-specific prerequisites
            if operation in ['start', 'resume']:
                return self._check_workflow_prerequisites()
            elif operation in ['merge', 'review', 'approve']:
                return self._check_merge_prerequisites()
            elif operation in ['commit']:
                return self._check_commit_prerequisites()
            
            return (0, "All prerequisites met")
            
        except Exception as e:
            error_msg = f"Error checking prerequisites: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def validate_before_operation(self, operation: str) -> Tuple[bool, str]:
        """
        Validate state before performing an operation.
        
        Args:
            operation: Operation to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Check prerequisites
            code, msg = self.check_prerequisites(operation)
            if code != 0:
                return (False, msg)
            
            # Validate operation-specific requirements
            if operation == 'start':
                if self.config.workflow_state:
                    return (False, "Workflow already in progress. Use --resume to continue.")
                
            elif operation == 'resume':
                if not self.config.workflow_state:
                    return (False, "No existing workflow to resume.")
                
            elif operation == 'commit':
                if not self.config.workflow_state:
                    return (False, "No active workflow. Start a workflow first.")
                
            elif operation == 'merge':
                if not self.config.workflow_state:
                    return (False, "No active workflow to merge.")
                
                current_branch = self.branches.get_current_branch()
                if current_branch == self.config.workflow_state.branch_name:
                    return (False, "Cannot merge into same branch. Switch to target branch first.")
            
            elif operation == 'review':
                if not self.config.workflow_state:
                    return (False, "No active workflow to review.")
            
            return (True, "Validation passed")
            
        except Exception as e:
            error_msg = f"Error validating before operation: {e}"
            self.logger.error(error_msg)
            return (False, error_msg)
    
    def _is_git_repository(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            code, stdout, stderr = run_git_command(
                ['rev-parse', '--git-dir'],
                cwd=self.repo_root
            )
            return code == 0
        except Exception:
            return False
    
    def _is_working_directory_clean(self) -> bool:
        """Check if working directory has no uncommitted changes."""
        try:
            code, stdout, stderr = run_git_command(
                ['status', '--porcelain'],
                cwd=self.repo_root
            )
            return code == 0 and not stdout.strip()
        except Exception:
            return False
    
    def _check_workflow_prerequisites(self) -> Tuple[int, str]:
        """Check prerequisites for starting a workflow."""
        try:
            # Check git configuration
            config_checks = [
                ('user.name', 'Git user name'),
                ('user.email', 'Git user email')
            ]
            
            for config_key, config_name in config_checks:
                code, stdout, stderr = run_git_command(
                    ['config', '--get', config_key],
                    cwd=self.repo_root
                )
                if code != 0 or not stdout.strip():
                    return (1, f"Git {config_name} not configured. Run: git config {config_key} '<value>'")
            
            # Check if branch naming is allowed
            current_branch = self.branches.get_current_branch()
            if self.branches.is_protected_branch(current_branch):
                return (1, f"Cannot start workflow from protected branch '{current_branch}'")
            
            return (0, "Workflow prerequisites met")
            
        except Exception as e:
            return (1, f"Error checking workflow prerequisites: {e}")
    
    def _check_merge_prerequisites(self) -> Tuple[int, str]:
        """Check prerequisites for merging."""
        try:
            # Check if there are uncommitted changes
            if not self._is_working_directory_clean():
                return (1, "Working directory is not clean. Commit or stash changes first.")
            
            # Check if merge is already in progress
            code, stdout, stderr = run_git_command(
                ['status', '--porcelain'],
                cwd=self.repo_root
            )
            if code == 0 and 'MERGE' in stdout:
                return (1, "Merge already in progress. Complete or abort current merge first.")
            
            return (0, "Merge prerequisites met")
            
        except Exception as e:
            return (1, f"Error checking merge prerequisites: {e}")
    
    def _check_commit_prerequisites(self) -> Tuple[int, str]:
        """Check prerequisites for committing."""
        try:
            # Check if there are staged changes
            code, stdout, stderr = run_git_command(
                ['diff', '--cached', '--name-only'],
                cwd=self.repo_root
            )
            if code != 0 or not stdout.strip():
                return (1, "No staged changes to commit. Use 'git add' to stage files first.")
            
            return (0, "Commit prerequisites met")
            
        except Exception as e:
            return (1, f"Error checking commit prerequisites: {e}")
    
    def validate_branch_name(self, branch_name: str) -> Tuple[bool, str]:
        """
        Validate a branch name.
        
        Args:
            branch_name: Branch name to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Check if branch name is empty
            if not branch_name or not branch_name.strip():
                return (False, "Branch name cannot be empty")
            
            # Sanitize input
            if not self.input_sanitizer.validate_string(branch_name):
                return (False, "Branch name contains invalid characters")
            
            # Check if branch name is too long
            if len(branch_name) > 255:
                return (False, "Branch name too long (max 255 characters)")
            
            # Check for invalid characters
            invalid_chars = ['..', '~', '^', ':', '\\', '*', '?', '[']
            for char in invalid_chars:
                if char in branch_name:
                    return (False, f"Branch name contains invalid character: '{char}'")
            
            # Check if branch name starts or ends with slash
            if branch_name.startswith('/') or branch_name.endswith('/'):
                return (False, "Branch name cannot start or end with '/'")
            
            # Check if branch name is a protected branch
            if self.branches.is_protected_branch(branch_name):
                return (False, f"Cannot use protected branch name: '{branch_name}'")
            
            # Check if branch already exists
            code, stdout, stderr = run_git_command(
                ['branch', '--list', branch_name],
                cwd=self.repo_root
            )
            if code == 0 and stdout.strip():
                return (False, f"Branch '{branch_name}' already exists")
            
            return (True, "Branch name is valid")
            
        except Exception as e:
            return (False, f"Error validating branch name: {e}")
    
    def validate_feature_name(self, feature_name: str) -> Tuple[bool, str]:
        """
        Validate a feature name for workflow.
        
        Args:
            feature_name: Feature name to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Check if feature name is empty
            if not feature_name or not feature_name.strip():
                return (False, "Feature name cannot be empty")
            
            # Sanitize input
            if not self.input_sanitizer.validate_string(feature_name):
                return (False, "Feature name contains invalid characters")
            
            # Check if feature name is too long
            if len(feature_name) > 100:
                return (False, "Feature name too long (max 100 characters)")
            
            return (True, "Feature name is valid")
            
        except Exception as e:
            return (False, f"Error validating feature name: {e}")
    
    def get_validation_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive validation report.
        
        Returns:
            Dictionary with validation information
        """
        report = {
            'repository': {
                'is_git_repo': self._is_git_repository(),
                'working_directory_clean': self._is_working_directory_clean()
            },
            'configuration': {
                'user_name_configured': self._is_git_configured('user.name'),
                'user_email_configured': self._is_git_configured('user.email')
            },
            'workflow': {
                'has_active_workflow': self.config.workflow_state is not None,
                'workflow_valid': False,
                'workflow_message': 'No workflow'
            },
            'branches': {
                'total_branches': len(self.config.branch_states),
                'valid_states': 0,
                'invalid_states': 0
            }
        }
        
        # Validate workflow state
        if self.config.workflow_state:
            is_valid, msg = validate_workflow_state(self.config.workflow_state.to_dict())
            report['workflow']['workflow_valid'] = is_valid
            report['workflow']['workflow_message'] = msg
        
        # Validate branch states
        for branch_name, branch_state in self.config.branch_states.items():
            is_valid, msg = validate_branch_state(branch_state.to_dict())
            if is_valid:
                report['branches']['valid_states'] += 1
            else:
                report['branches']['invalid_states'] += 1
        
        return report
    
    def _is_git_configured(self, config_key: str) -> bool:
        """Check if a git configuration is set."""
        try:
            code, stdout, stderr = run_git_command(
                ['config', '--get', config_key],
                cwd=self.repo_root
            )
            return code == 0 and stdout.strip()
        except Exception:
            return False