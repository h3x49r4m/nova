#!/usr/bin/env python3
"""
State Validator Module
Provides validation for state data to prevent execution with invalid data.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .exceptions import ErrorCode, ValidationError
from .constants import ValidationPatterns
from .schema_validator import SchemaValidator


class ValidationSeverity(Enum):
    """Severity levels for validation errors."""
    ERROR = "error"      # Critical: must be fixed before execution
    WARNING = "warning"  # Non-critical: execution possible but not recommended
    INFO = "info"        # Informational: suggestions for improvement


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    info: List[str]
    
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info
        }


class StateValidator:
    """
    Validates state data before execution.
    Prevents corrupt or invalid state from being processed.
    """
    
    def __init__(self, schema_dir: Optional[Path] = None):
        """
        Initialize state validator.
        
        Args:
            schema_dir: Directory containing JSON schemas for validation
        """
        self.schema_dir = schema_dir
        self.schema_validator = SchemaValidator(schema_dir) if schema_dir else None
    
    def validate_state(
        self,
        state: Dict[str, Any],
        state_type: str = "generic",
        strict: bool = True
    ) -> ValidationResult:
        """
        Validate state data comprehensively.
        
        Args:
            state: State dictionary to validate
            state_type: Type of state (for schema lookup)
            strict: If True, treat warnings as errors
        
        Returns:
            ValidationResult with validation findings
        """
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            info=[]
        )
        
        # 1. Basic structure validation
        self._validate_basic_structure(state, result)
        
        # 2. Schema validation if available
        if self.schema_validator:
            self._validate_schema(state, state_type, result)
        
        # 3. Content validation
        self._validate_content(state, result)
        
        # 4. Business logic validation
        self._validate_business_logic(state, result)
        
        # 5. Security validation
        self._validate_security(state, result)
        
        # Determine overall validity
        if strict:
            result.is_valid = not result.has_errors()
        else:
            result.is_valid = not result.has_errors()
        
        return result
    
    def _validate_basic_structure(self, state: Dict[str, Any], result: ValidationResult):
        """Validate basic state structure."""
        if not isinstance(state, dict):
            result.errors.append("State must be a dictionary")
            return
        
        if not state:
            result.warnings.append("State is empty")
        
        # Check for None values at top level
        for key, value in state.items():
            if value is None:
                result.warnings.append(f"State key '{key}' has None value")
    
    def _validate_schema(self, state: Dict[str, Any], state_type: str, result: ValidationResult):
        """Validate state against JSON schema."""
        try:
            schema_path = self.schema_dir / f"{state_type}.json"
            if schema_path.exists():
                is_valid, errors = self.schema_validator.validate(state, state_type)
                if not is_valid:
                    result.errors.extend(errors)
            else:
                result.info.append(f"No schema found for state type '{state_type}'")
        except Exception as e:
            result.warnings.append(f"Schema validation failed: {str(e)}")
    
    def _validate_content(self, state: Dict[str, Any], result: ValidationResult):
        """Validate content of state fields."""
        for key, value in state.items():
            # Validate branch names
            if 'branch' in key.lower() and isinstance(value, str):
                is_valid, error = self._validate_branch_name(value)
                if not is_valid:
                    result.errors.append(f"Invalid branch name in '{key}': {error}")
            
            # Validate file paths
            if 'path' in key.lower() and isinstance(value, str):
                is_valid, error = self._validate_file_path(value)
                if not is_valid:
                    result.errors.append(f"Invalid file path in '{key}': {error}")
            
            # Validate URLs
            if 'url' in key.lower() and isinstance(value, str):
                is_valid, error = self._validate_url(value)
                if not is_valid:
                    result.errors.append(f"Invalid URL in '{key}': {error}")
            
            # Validate email addresses
            if 'email' in key.lower() and isinstance(value, str):
                is_valid, error = self._validate_email(value)
                if not is_valid:
                    result.errors.append(f"Invalid email in '{key}': {error}")
            
            # Validate version strings
            if 'version' in key.lower() and isinstance(value, str):
                is_valid, error = self._validate_version(value)
                if not is_valid:
                    result.errors.append(f"Invalid version in '{key}': {error}")
    
    def _validate_business_logic(self, state: Dict[str, Any], result: ValidationResult):
        """Validate business logic constraints."""
        # Validate workflow-specific constraints
        if 'workflow' in state:
            self._validate_workflow_state(state['workflow'], result)
        
        # Validate branch-specific constraints
        if 'branches' in state:
            self._validate_branches_state(state['branches'], result)
        
        # Validate phase-specific constraints
        if 'phases' in state:
            self._validate_phases_state(state['phases'], result)
    
    def _validate_workflow_state(self, workflow: Dict[str, Any], result: ValidationResult):
        """Validate workflow state."""
        if not isinstance(workflow, dict):
            result.errors.append("Workflow state must be a dictionary")
            return
        
        # Check for required fields
        required_fields = ['name', 'status']
        for field in required_fields:
            if field not in workflow:
                result.errors.append(f"Workflow missing required field: {field}")
        
        # Validate status
        if 'status' in workflow:
            valid_statuses = ['active', 'completed', 'failed', 'paused']
            if workflow['status'] not in valid_statuses:
                result.errors.append(
                    f"Invalid workflow status: {workflow['status']}. "
                    f"Must be one of: {', '.join(valid_statuses)}"
                )
    
    def _validate_branches_state(self, branches: Any, result: ValidationResult):
        """Validate branches state."""
        if not isinstance(branches, list):
            result.errors.append("Branches must be a list")
            return
        
        for i, branch in enumerate(branches):
            if not isinstance(branch, dict):
                result.errors.append(f"Branch {i} must be a dictionary")
                continue
            
            # Check for required fields
            if 'name' not in branch:
                result.errors.append(f"Branch {i} missing required field: name")
            else:
                is_valid, error = self._validate_branch_name(branch['name'])
                if not is_valid:
                    result.errors.append(f"Branch {i} has invalid name: {error}")
            
            if 'status' not in branch:
                result.warnings.append(f"Branch {i} missing status field")
    
    def _validate_phases_state(self, phases: Any, result: ValidationResult):
        """Validate phases state."""
        if not isinstance(phases, list):
            result.errors.append("Phases must be a list")
            return
        
        for i, phase in enumerate(phases):
            if not isinstance(phase, dict):
                result.errors.append(f"Phase {i} must be a dictionary")
                continue
            
            # Check for required fields
            if 'name' not in phase:
                result.errors.append(f"Phase {i} missing required field: name")
            
            if 'status' not in phase:
                result.warnings.append(f"Phase {i} missing status field")
    
    def _validate_security(self, state: Dict[str, Any], result: ValidationResult):
        """Validate security concerns in state."""
        import re
        
        # Check for potential secrets in state
        state_str = json.dumps(state, default=str)
        
        # Check for API keys
        if re.search(r'api[_-]?key["\s]*[:=]["\s]*["\']?[a-zA-Z0-9_-]{20,}', state_str, re.IGNORECASE):
            result.warnings.append("State may contain API keys - consider using secure references")
        
        # Check for passwords
        if re.search(r'password["\s]*[:=]', state_str, re.IGNORECASE):
            result.warnings.append("State contains password field - ensure it is properly encrypted")
        
        # Check for tokens
        if re.search(r'token["\s]*[:=]["\s]*["\']?[a-zA-Z0-9_-]{20,}', state_str, re.IGNORECASE):
            result.warnings.append("State may contain tokens - consider using secure references")
        
        # Check for private keys
        if '-----BEGIN PRIVATE KEY-----' in state_str or '-----BEGIN RSA PRIVATE KEY-----' in state_str:
            result.errors.append("State contains private keys - this is a security violation")
    
    def _validate_branch_name(self, branch_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a branch name.
        
        Args:
            branch_name: Branch name to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not branch_name:
            return False, "Branch name cannot be empty"
        
        if len(branch_name) > ValidationPatterns.BRANCH_MAX_LENGTH.value:
            return False, f"Branch name too long (max {ValidationPatterns.BRANCH_MAX_LENGTH.value} characters)"
        
        # Check for invalid characters
        pattern = ValidationPatterns.BRANCH_NAME_PATTERN.value
        if not pattern.match(branch_name):
            return False, "Branch name contains invalid characters"
        
        # Check for reserved names
        reserved_names = ['master', 'main', 'develop', 'staging', 'production']
        if branch_name.lower() in reserved_names:
            return False, f"Branch name '{branch_name}' is reserved"
        
        # Check for control characters
        if any(ord(char) < 32 for char in branch_name):
            return False, "Branch name contains control characters"
        
        return True, None
    
    def _validate_file_path(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a file path.
        
        Args:
            file_path: File path to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_path:
            return False, "File path cannot be empty"
        
        # Check for null bytes
        if '\x00' in file_path:
            return False, "File path contains null bytes"
        
        # Check for encoded path traversal
        if '%2e%2e' in file_path.lower() or '%2e%2e%2f' in file_path.lower():
            return False, "File path contains encoded path traversal"
        
        # Check for shell injection patterns
        shell_patterns = [';', '|', '&', '$(', '`', '$$']
        if any(pattern in file_path for pattern in shell_patterns):
            return False, "File path contains shell injection patterns"
        
        return True, None
    
    def _validate_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a URL.
        
        Args:
            url: URL to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "URL cannot be empty"
        
        pattern = ValidationPatterns.URL_PATTERN.value
        if not pattern.match(url):
            return False, "URL format is invalid"
        
        return True, None
    
    def _validate_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate an email address.
        
        Args:
            email: Email address to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email:
            return False, "Email cannot be empty"
        
        pattern = ValidationPatterns.EMAIL_PATTERN.value
        if not pattern.match(email):
            return False, "Email format is invalid"
        
        return True, None
    
    def _validate_version(self, version: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a semantic version string.
        
        Args:
            version: Version string to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not version:
            return False, "Version cannot be empty"
        
        pattern = ValidationPatterns.VERSION_PATTERN.value
        if not pattern.match(version):
            return False, "Version format is invalid (expected X.Y.Z or X.Y.Z-prerelease+metadata)"
        
        return True, None
    
    def validate_and_raise(
        self,
        state: Dict[str, Any],
        state_type: str = "generic",
        strict: bool = True
    ) -> Dict[str, Any]:
        """
        Validate state and raise exception if invalid.
        
        Args:
            state: State dictionary to validate
            state_type: Type of state (for schema lookup)
            strict: If True, treat warnings as errors
        
        Returns:
            Validated state dictionary
        
        Raises:
            ValidationError: If state is invalid
        """
        result = self.validate_state(state, state_type, strict)
        
        if result.has_errors():
            error_msg = f"State validation failed:\n" + "\n".join(f"  - {e}" for e in result.errors)
            if result.has_warnings() and strict:
                error_msg += f"\nWarnings:\n" + "\n".join(f"  - {w}" for w in result.warnings)
            raise ValidationError(
                message=error_msg,
                code=ErrorCode.VALIDATION_ERROR,
                details=result.to_dict()
            )
        
        return state
    
    def validate_state_file(
        self,
        file_path: Path,
        state_type: str = "generic",
        strict: bool = True
    ) -> ValidationResult:
        """
        Validate a state file.
        
        Args:
            file_path: Path to state file
            state_type: Type of state (for schema lookup)
            strict: If True, treat warnings as errors
        
        Returns:
            ValidationResult with validation findings
        """
        try:
            if not file_path.exists():
                return ValidationResult(
                    is_valid=False,
                    errors=[f"State file does not exist: {file_path}"],
                    warnings=[],
                    info=[]
                )
            
            with open(file_path, 'r') as f:
                state = json.load(f)
            
            return self.validate_state(state, state_type, strict)
        
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Invalid JSON in state file: {str(e)}"],
                warnings=[],
                info=[]
            )
        except IOError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Could not read state file: {str(e)}"],
                warnings=[],
                info=[]
            )


class PreExecutionValidator:
    """
    Validates state before executing critical operations.
    Provides additional checks specific to execution context.
    """
    
    def __init__(self, state_validator: StateValidator):
        """
        Initialize pre-execution validator.
        
        Args:
            state_validator: Base state validator
        """
        self.state_validator = state_validator
    
    def validate_before_merge(
        self,
        state: Dict[str, Any],
        source_branch: str,
        target_branch: str
    ) -> ValidationResult:
        """
        Validate state before merging branches.
        
        Args:
            state: Current state
            source_branch: Branch being merged
            target_branch: Branch being merged into
        
        Returns:
            ValidationResult with validation findings
        """
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            info=[]
        )
        
        # Validate basic state
        base_result = self.state_validator.validate_state(state)
        result.errors.extend(base_result.errors)
        result.warnings.extend(base_result.warnings)
        result.info.extend(base_result.info)
        
        # Validate branches
        if 'branches' not in state:
            result.errors.append("State missing 'branches' field")
            result.is_valid = False
            return result
        
        # Check if source branch exists
        branches = state['branches']
        source_exists = any(b.get('name') == source_branch for b in branches if isinstance(b, dict))
        if not source_exists:
            result.errors.append(f"Source branch '{source_branch}' not found in state")
            result.is_valid = False
        
        # Check if target branch exists
        target_exists = any(b.get('name') == target_branch for b in branches if isinstance(b, dict))
        if not target_exists:
            result.errors.append(f"Target branch '{target_branch}' not found in state")
            result.is_valid = False
        
        # Check if source branch is in a mergeable state
        for branch in branches:
            if isinstance(branch, dict) and branch.get('name') == source_branch:
                status = branch.get('status', '')
                if status in ['failed', 'conflicted']:
                    result.errors.append(
                        f"Source branch '{source_branch}' is in '{status}' state and cannot be merged"
                    )
                    result.is_valid = False
        
        # Check for uncommitted changes
        if 'uncommitted_changes' in state and state['uncommitted_changes']:
            result.warnings.append("There are uncommitted changes in the state")
        
        return result
    
    def validate_before_phase_transition(
        self,
        state: Dict[str, Any],
        current_phase: str,
        next_phase: str
    ) -> ValidationResult:
        """
        Validate state before transitioning phases.
        
        Args:
            state: Current state
            current_phase: Current phase name
            next_phase: Next phase name
        
        Returns:
            ValidationResult with validation findings
        """
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            info=[]
        )
        
        # Validate basic state
        base_result = self.state_validator.validate_state(state)
        result.errors.extend(base_result.errors)
        result.warnings.extend(base_result.warnings)
        result.info.extend(base_result.info)
        
        # Validate phases
        if 'phases' not in state:
            result.errors.append("State missing 'phases' field")
            result.is_valid = False
            return result
        
        # Check if current phase exists and is active
        phases = state['phases']
        current_phase_found = False
        for phase in phases:
            if isinstance(phase, dict) and phase.get('name') == current_phase:
                current_phase_found = True
                status = phase.get('status', '')
                if status != 'active':
                    result.errors.append(
                        f"Current phase '{current_phase}' is not active (status: {status})"
                    )
                    result.is_valid = False
                break
        
        if not current_phase_found:
            result.errors.append(f"Current phase '{current_phase}' not found in state")
            result.is_valid = False
        
        # Check if next phase exists
        next_phase_found = any(
            p.get('name') == next_phase for p in phases if isinstance(p, dict)
        )
        if not next_phase_found:
            result.errors.append(f"Next phase '{next_phase}' not found in state")
            result.is_valid = False
        
        # Check if all dependencies for next phase are satisfied
        if 'dependencies' in state:
            deps = state['dependencies']
            unsatisfied = [d for d in deps if isinstance(d, dict) and d.get('satisfied') is False]
            if unsatisfied:
                result.errors.append(
                    f"Cannot transition to '{next_phase}' - {len(unsatisfied)} dependencies unsatisfied"
                )
                result.is_valid = False
        
        return result
    
    def validate_before_state_update(
        self,
        state: Dict[str, Any],
        update_key: str,
        update_value: Any
    ) -> ValidationResult:
        """
        Validate state before performing an update.
        
        Args:
            state: Current state
            update_key: Key to update
            update_value: New value
        
        Returns:
            ValidationResult with validation findings
        """
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            info=[]
        )
        
        # Validate basic state
        base_result = self.state_validator.validate_state(state)
        result.errors.extend(base_result.errors)
        result.warnings.extend(base_result.warnings)
        result.info.extend(base_result.info)
        
        # Validate update key
        if not update_key:
            result.errors.append("Update key cannot be empty")
            result.is_valid = False
        
        # Validate update value based on key
        if 'branch' in update_key.lower() and isinstance(update_value, str):
            is_valid, error = self.state_validator._validate_branch_name(update_value)
            if not is_valid:
                result.errors.append(f"Invalid branch name for '{update_key}': {error}")
                result.is_valid = False
        
        if 'path' in update_key.lower() and isinstance(update_value, str):
            is_valid, error = self.state_validator._validate_file_path(update_value)
            if not is_valid:
                result.errors.append(f"Invalid file path for '{update_key}': {error}")
                result.is_valid = False
        
        # Check if updating protected fields
        protected_fields = ['id', 'created_at', 'version']
        if update_key in protected_fields:
            result.warnings.append(f"Updating protected field '{update_key}' may cause issues")
        
        return result
