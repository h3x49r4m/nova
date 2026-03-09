"""Profile Manager - Manages environment profiles (dev/staging/prod).

This module provides functionality for managing multiple environment profiles
with different configurations for development, staging, and production environments.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from .exceptions import IFlowError, ErrorCode
from .json_schema_validator import JSONSchemaValidator


class ProfileType(Enum):
    """Types of environment profiles."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class Profile:
    """Represents an environment profile."""
    
    def __init__(
        self,
        name: str,
        profile_type: ProfileType,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a profile.
        
        Args:
            name: Profile name
            profile_type: Type of profile
            config: Profile configuration
        """
        self.name = name
        self.profile_type = profile_type
        self.config = config or {}
        self.inherits_from: Optional[str] = None
        self.variables: Dict[str, Any] = {}
        self.enabled: bool = True
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get a configuration value."""
        # Check profile-specific variables first
        if key in self.variables:
            return self.variables[key]
        
        # Check general config
        if key in self.config:
            return self.config[key]
        
        return default
    
    def set(self, key: str, value: Any):
        """Set a configuration value."""
        self.variables[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "name": self.name,
            "type": self.profile_type.value,
            "config": self.config,
            "variables": self.variables,
            "inherits_from": self.inherits_from,
            "enabled": self.enabled
        }


class ProfileManager:
    """Manages environment profiles."""
    
    def __init__(
        self,
        repo_root: Path,
        profile_dir: Optional[Path] = None,
        schema_validator: Optional[JSONSchemaValidator] = None
    ):
        """
        Initialize the profile manager.
        
        Args:
            repo_root: Repository root directory
            profile_dir: Directory for profile files
            schema_validator: Schema validator for profile files
        """
        self.repo_root = repo_root
        self.profile_dir = profile_dir or (repo_root / ".iflow" / "profiles")
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.schema_validator = schema_validator or JSONSchemaValidator(self.profile_dir)
        self.profiles: Dict[str, Profile] = {}
        self.active_profile: Optional[str] = None
        self._load_profiles()
    
    def _load_profiles(self):
        """Load all profiles from the profile directory."""
        if not self.profile_dir.exists():
            return
        
        for profile_file in self.profile_dir.glob("*.json"):
            try:
                with open(profile_file, 'r') as f:
                    data = json.load(f)
                
                profile_type = ProfileType(data.get("type", "development"))
                profile = Profile(
                    name=data.get("name", profile_file.stem),
                    profile_type=profile_type,
                    config=data.get("config", {})
                )
                
                profile.inherits_from = data.get("inherits_from")
                profile.variables = data.get("variables", {})
                profile.enabled = data.get("enabled", True)
                
                self.profiles[profile.name] = profile
            
            except (json.JSONDecodeError, IOError, ValueError):
                pass
    
    def _save_profile(self, profile: Profile):
        """Save a profile to file."""
        profile_file = self.profile_dir / f"{profile.name}.json"
        
        data = profile.to_dict()
        
        try:
            with open(profile_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save profile: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def create_profile(
        self,
        name: str,
        profile_type: ProfileType,
        config: Optional[Dict[str, Any]] = None,
        inherits_from: Optional[str] = None
    ) -> Profile:
        """
        Create a new profile.
        
        Args:
            name: Profile name
            profile_type: Type of profile
            config: Profile configuration
            inherits_from: Name of profile to inherit from
            
        Returns:
            Created Profile object
        """
        if name in self.profiles:
            raise IFlowError(
                f"Profile '{name}' already exists",
                ErrorCode.ALREADY_EXISTS
            )
        
        if inherits_from and inherits_from not in self.profiles:
            raise IFlowError(
                f"Parent profile '{inherits_from}' not found",
                ErrorCode.NOT_FOUND
            )
        
        profile = Profile(name, profile_type, config)
        profile.inherits_from = inherits_from
        
        self.profiles[name] = profile
        self._save_profile(profile)
        
        return profile
    
    def get_profile(self, name: str) -> Optional[Profile]:
        """Get a profile by name."""
        return self.profiles.get(name)
    
    def list_profiles(
        self,
        profile_type: Optional[ProfileType] = None,
        enabled_only: bool = False
    ) -> List[Profile]:
        """
        List profiles with optional filtering.
        
        Args:
            profile_type: Optional profile type filter
            enabled_only: Whether to only return enabled profiles
            
        Returns:
            List of matching profiles
        """
        profiles = list(self.profiles.values())
        
        if profile_type:
            profiles = [p for p in profiles if p.profile_type == profile_type]
        
        if enabled_only:
            profiles = [p for p in profiles if p.enabled]
        
        return profiles
    
    def delete_profile(self, name: str):
        """Delete a profile."""
        if name not in self.profiles:
            raise IFlowError(
                f"Profile '{name}' not found",
                ErrorCode.NOT_FOUND
            )
        
        if self.active_profile == name:
            raise IFlowError(
                f"Cannot delete active profile '{name}'",
                ErrorCode.INVALID_STATE
            )
        
        profile_file = self.profile_dir / f"{name}.json"
        if profile_file.exists():
            try:
                profile_file.unlink()
            except IOError as e:
                raise IFlowError(
                    f"Failed to delete profile file: {str(e)}",
                    ErrorCode.FILE_DELETE_ERROR
                )
        
        del self.profiles[name]
    
    def set_active_profile(self, name: str):
        """Set the active profile."""
        if name not in self.profiles:
            raise IFlowError(
                f"Profile '{name}' not found",
                ErrorCode.NOT_FOUND
            )
        
        if not self.profiles[name].enabled:
            raise IFlowError(
                f"Profile '{name}' is disabled",
                ErrorCode.INVALID_STATE
            )
        
        self.active_profile = name
    
    def get_active_profile(self) -> Optional[Profile]:
        """Get the active profile."""
        if self.active_profile:
            return self.profiles.get(self.active_profile)
        return None
    
    def get_config(
        self,
        profile_name: Optional[str] = None,
        include_inherited: bool = True
    ) -> Dict[str, Any]:
        """
        Get configuration for a profile.
        
        Args:
            profile_name: Name of profile (uses active if None)
            include_inherited: Whether to include inherited configuration
            
        Returns:
            Merged configuration dictionary
        """
        if profile_name is None:
            profile_name = self.active_profile
        
        if not profile_name or profile_name not in self.profiles:
            return {}
        
        config = {}
        
        if include_inherited:
            # Build inheritance chain
            chain = self._get_inheritance_chain(profile_name)
            
            # Merge from parent to child
            for ancestor_name in reversed(chain):
                ancestor = self.profiles[ancestor_name]
                config.update(ancestor.config)
                config.update(ancestor.variables)
        
        # Add profile-specific config
        profile = self.profiles[profile_name]
        config.update(profile.config)
        config.update(profile.variables)
        
        return config
    
    def _get_inheritance_chain(self, profile_name: str, visited: Optional[Set[str]] = None) -> List[str]:
        """
        Get the inheritance chain for a profile.
        
        Args:
            profile_name: Name of profile
            visited: Set of already visited profiles (to detect cycles)
            
        Returns:
            List of profile names in inheritance order (child first)
        """
        if visited is None:
            visited = set()
        
        if profile_name in visited:
            raise IFlowError(
                f"Circular dependency detected in profile inheritance: {profile_name}",
                ErrorCode.CIRCULAR_DEPENDENCY
            )
        
        visited.add(profile_name)
        
        profile = self.profiles.get(profile_name)
        if not profile:
            return []
        
        chain = [profile_name]
        
        if profile.inherits_from:
            parent_chain = self._get_inheritance_chain(profile.inherits_from, visited.copy())
            chain.extend(parent_chain)
        
        return chain
    
    def export_profile(
        self,
        profile_name: str,
        output_file: Path,
        include_inherited: bool = True
    ):
        """
        Export a profile configuration to a file.
        
        Args:
            profile_name: Name of profile to export
            output_file: Path to output file
            include_inherited: Whether to include inherited configuration
        """
        config = self.get_config(profile_name, include_inherited)
        
        output_data = {
            "profile": profile_name,
            "type": self.profiles[profile_name].profile_type.value,
            "config": config
        }
        
        try:
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to export profile: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def import_profile(
        self,
        input_file: Path,
        name: Optional[str] = None,
        profile_type: Optional[ProfileType] = None
    ) -> Profile:
        """
        Import a profile from a file.
        
        Args:
            input_file: Path to import file
            name: Optional name for the profile
            profile_type: Optional profile type
            
        Returns:
            Imported Profile object
        """
        try:
            with open(input_file, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise IFlowError(
                f"Failed to import profile: {str(e)}",
                ErrorCode.FILE_READ_ERROR
            )
        
        profile_name = name or data.get("name")
        profile_type_name = data.get("type", "development")
        
        if not profile_name:
            raise IFlowError(
                "Profile name is required",
                ErrorCode.VALIDATION_ERROR
            )
        
        profile_type = profile_type or ProfileType(profile_type_name)
        config = data.get("config", {})
        
        return self.create_profile(profile_name, profile_type, config)
    
    def validate_profile(self, profile_name: str) -> Tuple[bool, List[str]]:
        """
        Validate a profile configuration.
        
        Args:
            profile_name: Name of profile to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if profile_name not in self.profiles:
            return False, [f"Profile '{profile_name}' not found"]
        
        errors = []
        profile = self.profiles[profile_name]
        
        # Check inheritance chain for cycles
        try:
            self._get_inheritance_chain(profile_name)
        except IFlowError as e:
            errors.append(str(e))
        
        # Validate required fields
        if not profile.name:
            errors.append("Profile name is required")
        
        if not profile.config and not profile.variables:
            errors.append("Profile must have either config or variables")
        
        # Check for circular dependencies in variables
        # (This is a simplified check - could be more sophisticated)
        config = self.get_config(profile_name, include_inherited=True)
        
        # Validate against schema if available
        schema_name = f"profile-{profile.profile_type.value}"
        is_valid, schema_errors = self.schema_validator.validate(config, schema_name)
        if not is_valid:
            errors.extend(schema_errors)
        
        return len(errors) == 0, errors
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get profile statistics."""
        type_counts = {}
        enabled_count = 0
        
        for profile in self.profiles.values():
            profile_type = profile.profile_type.value
            type_counts[profile_type] = type_counts.get(profile_type, 0) + 1
            
            if profile.enabled:
                enabled_count += 1
        
        return {
            "total_profiles": len(self.profiles),
            "enabled_profiles": enabled_count,
            "disabled_profiles": len(self.profiles) - enabled_count,
            "type_counts": type_counts,
            "active_profile": self.active_profile
        }
    
    def generate_env_file(
        self,
        profile_name: Optional[str] = None,
        output_file: Optional[Path] = None
    ) -> str:
        """
        Generate a .env file from profile configuration.
        
        Args:
            profile_name: Name of profile (uses active if None)
            output_file: Optional path to save .env file
            
        Returns:
            .env file content
        """
        config = self.get_config(profile_name, include_inherited=True)
        
        lines = []
        lines.append(f"# Environment file generated from profile: {profile_name or self.active_profile}")
        lines.append(f"# Generated at: {self._get_timestamp()}")
        lines.append("")
        
        for key, value in config.items():
            if isinstance(value, bool):
                value = "true" if value else "false"
            elif isinstance(value, (list, dict)):
                value = json.dumps(value)
            else:
                value = str(value)
            
            lines.append(f"{key.upper()}={value}")
        
        content = "\n".join(lines)
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(content)
            except IOError as e:
                raise IFlowError(
                    f"Failed to write .env file: {str(e)}",
                    ErrorCode.FILE_WRITE_ERROR
                )
        
        return content
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()


def create_profile_manager(
    repo_root: Path,
    profile_dir: Optional[Path] = None,
    schema_validator: Optional[JSONSchemaValidator] = None
) -> ProfileManager:
    """Create a profile manager instance."""
    return ProfileManager(repo_root, profile_dir, schema_validator)