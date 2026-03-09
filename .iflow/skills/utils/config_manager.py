#!/usr/bin/env python3
"""
Configuration Manager
Centralized configuration management for skills and pipelines.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

from .exceptions import IFlowError, ErrorCode, ValidationError


class SkillType(Enum):
    """Types of skills."""
    ROLE = "role"
    PIPELINE = "pipeline"
    WORKFLOW = "workflow"


class ConfigManager:
    """Centralized configuration manager for skills and pipelines."""

    # Standard configuration schema
    STANDARD_SCHEMA = {
        "name": str,
        "version": str,
        "description": str,
        "type": str,
        "capabilities": list,
        "dependencies": list,
        "settings": dict
    }

    # Default configuration values
    DEFAULT_CONFIG = {
        "version": "1.0.0",
        "type": "role",
        "capabilities": [],
        "dependencies": [],
        "settings": {
            "type": "role",
            "domains": {},
            "compatible_pipelines": []
        }
    }

    @staticmethod
    def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load configuration from a JSON file.

        Args:
            config_path: Path to the configuration file

        Returns:
            Configuration dictionary

        Raises:
            IFlowError: If file not found or invalid JSON
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise IFlowError(
                f"Configuration file not found: {config_path}",
                ErrorCode.FILE_NOT_FOUND
            )

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            raise IFlowError(
                f"Invalid JSON in configuration file: {e}",
                ErrorCode.CONFIG_INVALID
            )

        return config

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate configuration against standard schema.

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check required fields
        required_fields = ["name", "version", "description", "type"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        # Check version format (semantic versioning)
        if "version" in config:
            version = config["version"]
            if not isinstance(version, str) or not ConfigManager._is_valid_semver(version):
                errors.append(f"Invalid version format: {version}")

        # Check type
        if "type" in config:
            skill_type = config["type"]
            try:
                SkillType(skill_type)
            except ValueError:
                errors.append(f"Invalid skill type: {skill_type}")

        # Check capabilities
        if "capabilities" in config:
            capabilities = config["capabilities"]
            if not isinstance(capabilities, list):
                errors.append("Capabilities must be a list")

        # Check dependencies
        if "dependencies" in config:
            dependencies = config["dependencies"]
            if not isinstance(dependencies, list):
                errors.append("Dependencies must be a list")
            else:
                for i, dep in enumerate(dependencies):
                    if not isinstance(dep, dict):
                        errors.append(f"Dependency {i} must be a dictionary")
                    elif "name" not in dep:
                        errors.append(f"Dependency {i} missing 'name' field")

        return (len(errors) == 0, errors)

    @staticmethod
    def _is_valid_semver(version: str) -> bool:
        """
        Check if version string follows semantic versioning.

        Args:
            version: Version string

        Returns:
            True if valid semver, False otherwise
        """
        import re
        pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*)?(\+[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*)?$'
        return bool(re.match(pattern, version))

    @staticmethod
    def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configurations, with override taking precedence.

        Args:
            base_config: Base configuration
            override_config: Override configuration

        Returns:
            Merged configuration
        """
        merged = base_config.copy()

        for key, value in override_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = ConfigManager.merge_configs(merged[key], value)
            else:
                merged[key] = value

        return merged

    @staticmethod
    def get_skill_config(skill_name: str, skills_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Get configuration for a specific skill.

        Args:
            skill_name: Name of the skill
            skills_dir: Directory containing skills (defaults to .iflow/skills)

        Returns:
            Skill configuration

        Raises:
            IFlowError: If skill not found or config invalid
        """
        if skills_dir is None:
            skills_dir = Path.cwd() / '.iflow' / 'skills'
        else:
            skills_dir = Path(skills_dir)

        skill_dir = skills_dir / skill_name
        config_file = skill_dir / 'config.json'

        if not skill_dir.exists():
            raise IFlowError(
                f"Skill not found: {skill_name}",
                ErrorCode.SKILL_NOT_FOUND
            )

        config = ConfigManager.load_config(config_file)
        is_valid, errors = ConfigManager.validate_config(config)

        if not is_valid:
            raise IFlowError(
                f"Invalid configuration for skill {skill_name}: {', '.join(errors)}",
                ErrorCode.CONFIG_INVALID
            )

        return config

    @staticmethod
    def get_compatible_pipelines(skill_config: Dict[str, Any]) -> List[str]:
        """
        Get list of pipelines compatible with a skill.

        Args:
            skill_config: Skill configuration

        Returns:
            List of compatible pipeline names
        """
        settings = skill_config.get("settings", {})
        compatible_pipelines = settings.get("compatible_pipelines", [])

        # If compatible_pipelines is ["*"], return all pipelines
        if compatible_pipelines == ["*"]:
            return ["*"]

        return compatible_pipelines

    @staticmethod
    def get_skill_dependencies(skill_config: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Get dependencies for a skill.

        Args:
            skill_config: Skill configuration

        Returns:
            List of dependencies
        """
        return skill_config.get("dependencies", [])

    @staticmethod
    def check_compatibility(skill_config: Dict[str, Any], pipeline_config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Check if a skill is compatible with a pipeline.

        Args:
            skill_config: Skill configuration
            pipeline_config: Pipeline configuration

        Returns:
            Tuple of (is_compatible, error_messages)
        """
        errors = []
        skill_name = skill_config.get("name", "unknown")

        # Check compatible pipelines
        compatible_pipelines = ConfigManager.get_compatible_pipelines(skill_config)

        if compatible_pipelines != ["*"]:
            pipeline_name = pipeline_config.get("name", "")
            if pipeline_name not in compatible_pipelines:
                errors.append(f"Skill {skill_name} is not compatible with pipeline {pipeline_name}")

        # Check dependencies
        skill_dependencies = ConfigManager.get_skill_dependencies(skill_config)
        pipeline_skills = pipeline_config.get("skills", {})

        for dep in skill_dependencies:
            dep_name = dep.get("name")
            if dep_name not in pipeline_skills:
                errors.append(f"Skill {skill_name} requires dependency {dep_name}")

        return (len(errors) == 0, errors)

    @staticmethod
    def save_config(config: Dict[str, Any], config_path: Union[str, Path]) -> None:
        """
        Save configuration to a JSON file.

        Args:
            config: Configuration dictionary
            config_path: Path to save the configuration

        Raises:
            IFlowError: If unable to save configuration
        """
        config_path = Path(config_path)

        # Validate before saving
        is_valid, errors = ConfigManager.validate_config(config)
        if not is_valid:
            raise ValidationError(
                f"Invalid configuration: {', '.join(errors)}",
                ErrorCode.CONFIG_INVALID
            )

        try:
            # Create parent directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except (IOError, OSError) as e:
            raise IFlowError(
                f"Failed to save configuration to {config_path}: {e}",
                ErrorCode.FILE_WRITE_ERROR
            )

    @staticmethod
    def create_default_config(name: str, description: str, skill_type: SkillType = SkillType.ROLE) -> Dict[str, Any]:
        """
        Create a default configuration for a skill.

        Args:
            name: Name of the skill
            description: Description of the skill
            skill_type: Type of skill (role, pipeline, workflow)

        Returns:
            Default configuration dictionary
        """
        config = ConfigManager.DEFAULT_CONFIG.copy()
        config["name"] = name
        config["description"] = description
        config["type"] = skill_type.value
        config["settings"]["type"] = skill_type.value

        return config

    @staticmethod
    def get_config_schema() -> Dict[str, Any]:
        """
        Get the standard configuration schema.

        Returns:
            Configuration schema
        """
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+"},
                "description": {"type": "string"},
                "type": {"type": "string", "enum": ["role", "pipeline", "workflow"]},
                "capabilities": {"type": "array", "items": {"type": "string"}},
                "dependencies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "min_version": {"type": "string"},
                            "max_version": {"type": "string"}
                        },
                        "required": ["name"]
                    }
                },
                "settings": {"type": "object"}
            },
            "required": ["name", "version", "description", "type"]
        }