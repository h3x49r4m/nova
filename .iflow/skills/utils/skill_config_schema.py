"""Unified Skill Configuration Schema.

This module defines the unified configuration schema for all skills and pipelines
in the iFlow CLI Skills system, providing consistent validation and structure.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple



# Unified Schema Definition
UNIFIED_SKILL_CONFIG_SCHEMA = {
    "type": "object",
    "required": ["name", "version", "type", "description"],
    "properties": {
        "name": {
            "type": "string",
            "pattern": r"^[a-z][a-z0-9-]*$",
            "description": "Skill/pipeline name (lowercase, alphanumeric, hyphens)"
        },
        "version": {
            "type": "string",
            "pattern": r"^\d+\.\d+\.\d+$",
            "description": "Semantic version (major.minor.patch)"
        },
        "type": {
            "type": "string",
            "enum": ["role", "pipeline"],
            "description": "Type of configuration"
        },
        "description": {
            "type": "string",
            "minLength": 10,
            "description": "Brief description of the skill/pipeline"
        },
        "capabilities": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "description": "List of capabilities provided"
        },
        "dependencies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "min_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"}
                },
                "required": ["name", "min_version"]
            },
            "description": "List of dependencies with version constraints"
        },
        "settings": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "categories": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "domains": {
                    "type": "object",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "supported": {"type": "boolean"},
                            "technologies": {"type": "array", "items": {"type": "string"}},
                            "reason": {"type": "string"}
                        }
                    }
                },
                "compatible_pipelines": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "update_mode": {
                    "type": "string",
                    "enum": ["compatible", "strict"]
                },
                "python_min": {
                    "type": "string",
                    "pattern": r"^\d+\.\d+$"
                },
                "node_min": {
                    "type": "string",
                    "pattern": r"^\d+$"
                }
            },
            "description": "Skill-specific settings and configurations"
        }
    }
}


class SkillConfigValidator:
    """Validates skill and pipeline configurations against unified schema."""
    
    def __init__(self, strict: bool = False):
        """
        Initialize the validator.
        
        Args:
            strict: If True, reject configs with unknown fields
        """
        self.strict = strict
    
    def validate(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a configuration dictionary.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Validate required fields
        required_fields = ["name", "version", "type", "description"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return False, errors
        
        # Validate name
        if not self._validate_name(config["name"]):
            errors.append(
                f"Invalid name '{config['name']}': must be lowercase, "
                "start with letter, contain only alphanumeric and hyphens"
            )
        
        # Validate version
        if not self._validate_semantic_version(config["version"]):
            errors.append(
                f"Invalid version '{config['version']}': must be semantic version (major.minor.patch)"
            )
        
        # Validate type
        if config["type"] not in ["role", "pipeline"]:
            errors.append(
                f"Invalid type '{config['type']}': must be 'role' or 'pipeline'"
            )
        
        # Validate description
        if not isinstance(config["description"], str) or len(config["description"]) < 10:
            errors.append(
                f"Invalid description: must be a string with at least 10 characters"
            )
        
        # Validate capabilities if present
        if "capabilities" in config:
            if not isinstance(config["capabilities"], list):
                errors.append("Capabilities must be an array")
            elif len(config["capabilities"]) == 0:
                errors.append("Capabilities array must have at least one item")
            else:
                for i, cap in enumerate(config["capabilities"]):
                    if not isinstance(cap, str) or not cap:
                        errors.append(f"Capability at index {i} must be a non-empty string")
        
        # Validate dependencies if present
        if "dependencies" in config:
            if not isinstance(config["dependencies"], list):
                errors.append("Dependencies must be an array")
            else:
                for i, dep in enumerate(config["dependencies"]):
                    dep_errors = self._validate_dependency(dep, i)
                    errors.extend(dep_errors)
        
        # Validate settings if present
        if "settings" in config:
            if not isinstance(config["settings"], dict):
                errors.append("Settings must be an object")
            else:
                setting_errors = self._validate_settings(config["settings"], config["type"])
                errors.extend(setting_errors)
        
        # Check for unknown fields in strict mode
        if self.strict:
            known_fields = set(UNIFIED_SKILL_CONFIG_SCHEMA["properties"].keys())
            unknown_fields = set(config.keys()) - known_fields
            if unknown_fields:
                errors.append(f"Unknown fields: {', '.join(unknown_fields)}")
        
        return len(errors) == 0, errors
    
    def validate_file(self, config_path: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate a configuration file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Tuple of (is_valid, error_messages, loaded_config)
        """
        if not config_path.exists():
            return False, [f"Configuration file not found: {config_path}"], {}
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {str(e)}"], {}
        except Exception as e:
            return False, [f"Failed to read file: {str(e)}"], {}
        
        is_valid, errors = self.validate(config)
        return is_valid, errors, config
    
    def normalize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a configuration to match the unified schema.
        
        Args:
            config: Configuration dictionary to normalize
            
        Returns:
            Normalized configuration dictionary
        """
        normalized = {}
        
        # Copy standard fields
        for field in ["name", "version", "type", "description"]:
            if field in config:
                normalized[field] = config[field]
        
        # Ensure type is set
        if "type" not in normalized:
            normalized["type"] = "role"  # Default to role
        
        # Normalize capabilities
        if "capabilities" in config:
            # Handle nested capabilities structure
            if isinstance(config["capabilities"], dict):
                if "capabilities" in config["capabilities"]:
                    normalized["capabilities"] = config["capabilities"]["capabilities"]
                else:
                    normalized["capabilities"] = list(config["capabilities"].keys())
            elif isinstance(config["capabilities"], list):
                normalized["capabilities"] = config["capabilities"]
            else:
                normalized["capabilities"] = []
        else:
            normalized["capabilities"] = []
        
        # Normalize dependencies
        if "dependencies" in config:
            if isinstance(config["dependencies"], dict):
                # Convert object to array format
                deps = []
                for name, version_info in config["dependencies"].items():
                    if isinstance(version_info, dict) and "min_version" in version_info:
                        deps.append({
                            "name": name,
                            "min_version": version_info["min_version"]
                        })
                    else:
                        deps.append({
                            "name": name,
                            "min_version": "1.0.0"  # Default version
                        })
                normalized["dependencies"] = deps
            elif isinstance(config["dependencies"], list):
                normalized["dependencies"] = config["dependencies"]
            else:
                normalized["dependencies"] = []
        else:
            normalized["dependencies"] = []
        
        # Normalize settings - preserve all original settings
        if "settings" in config:
            normalized["settings"] = config["settings"].copy()
            
            # Ensure settings has type field
            if "type" not in normalized["settings"]:
                normalized["settings"]["type"] = normalized["type"]
            
            # Ensure settings has domains
            if "domains" not in normalized["settings"]:
                normalized["settings"]["domains"] = {}
            
            # Ensure settings has compatible_pipelines
            if "compatible_pipelines" not in normalized["settings"]:
                normalized["settings"]["compatible_pipelines"] = []
        else:
            # Create default settings structure
            normalized["settings"] = {
                "type": normalized["type"],
                "domains": {},
                "compatible_pipelines": []
            }
        
        # Copy any additional fields (preserve them)
        standard_fields = {"name", "version", "type", "description", "capabilities", "dependencies", "settings"}
        for key, value in config.items():
            if key not in standard_fields:
                normalized[key] = value
        
        return normalized
    
    def _validate_name(self, name: str) -> bool:
        """Validate skill/pipeline name format."""
        pattern = r"^[a-z][a-z0-9-]*$"
        return bool(re.match(pattern, name))
    
    def _validate_semantic_version(self, version: str) -> bool:
        """Validate semantic version format."""
        pattern = r"^\d+\.\d+\.\d+$"
        return bool(re.match(pattern, version))
    
    def _validate_dependency(self, dep: Any, index: int) -> List[str]:
        """Validate a single dependency entry."""
        errors = []
        
        if not isinstance(dep, dict):
            errors.append(f"Dependency at index {index} must be an object")
            return errors
        
        if "name" not in dep:
            errors.append(f"Dependency at index {index} missing 'name' field")
        elif not isinstance(dep["name"], str) or not dep["name"]:
            errors.append(f"Dependency at index {index} has invalid 'name'")
        
        if "min_version" not in dep:
            errors.append(f"Dependency at index {index} missing 'min_version' field")
        elif not self._validate_semantic_version(dep["min_version"]):
            errors.append(
                f"Dependency at index {index} has invalid 'min_version': {dep['min_version']}"
            )
        
        return errors
    
    def _validate_settings(self, settings: Dict[str, Any], config_type: str) -> List[str]:
        """Validate settings object."""
        errors = []
        
        # Validate type in settings if present
        if "type" in settings and settings["type"] not in ["role", "pipeline"]:
            errors.append(
                f"Invalid settings type '{settings['type']}': must be 'role' or 'pipeline'"
            )
        
        # Validate domains if present
        if "domains" in settings:
            if not isinstance(settings["domains"], dict):
                errors.append("Settings domains must be an object")
            else:
                for domain_name, domain_config in settings["domains"].items():
                    if not isinstance(domain_config, dict):
                        errors.append(f"Domain '{domain_name}' config must be an object")
                        continue
                    
                    # Check for boolean flags
                    has_enabled = "enabled" in domain_config
                    has_supported = "supported" in domain_config
                    
                    if has_enabled and not isinstance(domain_config["enabled"], bool):
                        errors.append(f"Domain '{domain_name}' enabled must be boolean")
                    
                    if has_supported and not isinstance(domain_config["supported"], bool):
                        errors.append(f"Domain '{domain_name}' supported must be boolean")
                    
                    # Validate technologies if present
                    if "technologies" in domain_config:
                        if not isinstance(domain_config["technologies"], list):
                            errors.append(f"Domain '{domain_name}' technologies must be an array")
        
        # Validate compatible_pipelines if present
        if "compatible_pipelines" in settings:
            if not isinstance(settings["compatible_pipelines"], list):
                errors.append("Settings compatible_pipelines must be an array")
        
        # Validate update_mode if present
        if "update_mode" in settings:
            if settings["update_mode"] not in ["compatible", "strict"]:
                errors.append(
                    f"Invalid update_mode '{settings['update_mode']}': "
                    "must be 'compatible' or 'strict'"
                )
        
        # Validate python_min if present
        if "python_min" in settings:
            if not re.match(r"^\d+\.\d+$", str(settings["python_min"])):
                errors.append(f"Invalid python_min format: {settings['python_min']}")
        
        # Validate node_min if present
        if "node_min" in settings:
            if not re.match(r"^\d+$", str(settings["node_min"])):
                errors.append(f"Invalid node_min format: {settings['node_min']}")
        
        return errors


def validate_skill_config(config_path: Path) -> Tuple[int, str]:
    """
    Convenience function to validate a skill configuration file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Tuple of (exit_code, message)
    """
    validator = SkillConfigValidator()
    is_valid, errors, config = validator.validate_file(config_path)
    
    if not is_valid:
        return 1, "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
    
    return 0, f"Configuration is valid: {config_path}"


def normalize_skill_config_file(input_path: Path, output_path: Optional[Path] = None) -> Tuple[int, str]:
    """
    Normalize a skill configuration file to match the unified schema.
    
    Args:
        input_path: Path to the input configuration file
        output_path: Path to save normalized config (defaults to input_path)
        
    Returns:
        Tuple of (exit_code, message)
    """
    if output_path is None:
        output_path = input_path
    
    validator = SkillConfigValidator()
    is_valid, errors, config = validator.validate_file(input_path)
    
    if not is_valid:
        return 1, f"Cannot normalize invalid config:\n" + "\n".join(f"  - {e}" for e in errors)
    
    normalized = validator.normalize_config(config)
    
    try:
        with open(output_path, 'w') as f:
            json.dump(normalized, f, indent=2)
        return 0, f"Normalized configuration saved to: {output_path}"
    except Exception as e:
        return 1, f"Failed to save normalized configuration: {str(e)}"


def migrate_all_configs(config_dir: Path, dry_run: bool = False) -> Tuple[int, str, List[Dict[str, Any]]]:
    """
    Migrate all configuration files in a directory to the unified schema.
    
    Args:
        config_dir: Directory containing configuration files
        dry_run: If True, don't actually modify files
        
    Returns:
        Tuple of (exit_code, message, results)
    """
    validator = SkillConfigValidator()
    results = []
    
    if not config_dir.exists():
        return 1, f"Configuration directory not found: {config_dir}", []
    
    # Find all config.json files
    config_files = list(config_dir.glob("**/config.json"))
    
    if not config_files:
        return 0, "No configuration files found.", []
    
    for config_file in config_files:
        is_valid, errors, config = validator.validate_file(config_file)
        
        if not is_valid:
            # Try to normalize
            try:
                normalized = validator.normalize_config(config)
                results.append({
                    "file": str(config_file),
                    "status": "normalized",
                    "message": "Configuration normalized"
                })
                
                if not dry_run:
                    with open(config_file, 'w') as f:
                        json.dump(normalized, f, indent=2)
            except Exception as e:
                results.append({
                    "file": str(config_file),
                    "status": "error",
                    "message": f"Failed to normalize: {str(e)}"
                })
        else:
            # Check if already normalized
            normalized = validator.normalize_config(config)
            if normalized == config:
                results.append({
                    "file": str(config_file),
                    "status": "valid",
                    "message": "Already normalized"
                })
            else:
                results.append({
                    "file": str(config_file),
                    "status": "needs_normalize",
                    "message": "Valid but not normalized"
                })
    
    # Summary
    normalized_count = sum(1 for r in results if r["status"] == "normalized")
    valid_count = sum(1 for r in results if r["status"] == "valid")
    error_count = sum(1 for r in results if r["status"] == "error")
    
    summary = (
        f"Processed {len(results)} configuration files: "
        f"{normalized_count} normalized, {valid_count} already valid, {error_count} errors"
    )
    
    if dry_run:
        summary += " (dry run, no files modified)"
    
    return 0, summary, results