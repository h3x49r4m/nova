"""Config Validator - Validates configuration files against schemas.

This module provides functionality for validating various configuration
files against their corresponding JSON schemas.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .schema_validator import SchemaValidator


class ConfigValidator:
    """Validates configuration files against schemas."""
    
    def __init__(self, schema_dir: Optional[Path] = None):
        """
        Initialize config validator.
        
        Args:
            schema_dir: Directory containing schema files
        """
        self.schema_dir = schema_dir
        self.schema_validator = SchemaValidator(schema_dir)
    
    def validate_pipeline_config(self, config_path: Path) -> Tuple[int, str]:
        """
        Validate a pipeline configuration file.
        
        Args:
            config_path: Path to the pipeline configuration file
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        try:
            if not config_path.exists():
                return 1, f"Configuration file not found: {config_path}"
            
            # Load configuration
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Validate against schema
            is_valid, errors = self.schema_validator.validate(config, 'pipeline-config')
            
            if not is_valid:
                return 1, f"Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            
            # Additional validation checks
            additional_errors = self._validate_pipeline_config_additional(config)
            
            if additional_errors:
                return 1, "Additional validation failed:\n" + "\n".join(f"  - {e}" for e in additional_errors)
            
            return 0, f"Pipeline configuration is valid: {config_path}"
        
        except json.JSONDecodeError as e:
            return 1, f"Invalid JSON in configuration file: {str(e)}"
        except Exception as e:
            return 1, f"Failed to validate configuration: {str(e)}"
    
    def validate_skill_config(self, config_path: Path) -> Tuple[int, str]:
        """
        Validate a skill configuration file.
        
        Args:
            config_path: Path to the skill configuration file
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        try:
            if not config_path.exists():
                return 1, f"Configuration file not found: {config_path}"
            
            # Load configuration
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Basic validation for skill config
            required_fields = ['version', 'name', 'type', 'description', 'capabilities']
            errors = []
            
            for field in required_fields:
                if field not in config:
                    errors.append(f"Missing required field: {field}")
            
            # Validate version format
            if 'version' in config:
                if not self._validate_semantic_version(config['version']):
                    errors.append(f"Invalid version format: {config['version']}")
            
            # Validate type
            if 'type' in config:
                valid_types = ['skill', 'pipeline']
                if config['type'] not in valid_types:
                    errors.append(f"Invalid type: {config['type']}. Must be one of {valid_types}")
            
            if errors:
                return 1, "Skill configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            
            return 0, f"Skill configuration is valid: {config_path}"
        
        except json.JSONDecodeError as e:
            return 1, f"Invalid JSON in configuration file: {str(e)}"
        except Exception as e:
            return 1, f"Failed to validate configuration: {str(e)}"
    
    def validate_all_configs(self, config_dir: Path) -> Tuple[int, str, List[Dict[str, Any]]]:
        """
        Validate all configuration files in a directory.
        
        Args:
            config_dir: Directory containing configuration files
            
        Returns:
            Tuple of (exit_code, output_message, results_list)
        """
        results = []
        
        if not config_dir.exists():
            return 1, f"Configuration directory not found: {config_dir}", []
        
        # Find all config.json files
        config_files = list(config_dir.glob("**/config.json"))
        
        if not config_files:
            return 0, "No configuration files found.", []
        
        for config_file in config_files:
            # Determine config type based on parent directory
            parent_name = config_file.parent.name
            
            if parent_name.startswith("team-pipeline-"):
                code, output = self.validate_pipeline_config(config_file)
                results.append({
                    "file": str(config_file),
                    "type": "pipeline",
                    "valid": code == 0,
                    "message": output
                })
            else:
                code, output = self.validate_skill_config(config_file)
                results.append({
                    "file": str(config_file),
                    "type": "skill",
                    "valid": code == 0,
                    "message": output
                })
        
        # Summary
        valid_count = sum(1 for r in results if r["valid"])
        total_count = len(results)
        
        if valid_count == total_count:
            return 0, f"All {total_count} configuration files are valid.", results
        else:
            invalid_count = total_count - valid_count
            return 1, f"{invalid_count} of {total_count} configuration files failed validation.", results
    
    def _validate_pipeline_config_additional(self, config: Dict[str, Any]) -> List[str]:
        """
        Perform additional validation checks on pipeline configuration.
        
        Args:
            config: Pipeline configuration dictionary
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Validate stages
        if "stages" in config:
            stages = config["stages"]
            orders = set()
            
            for i, stage in enumerate(stages):
                # Check for duplicate orders
                order = stage.get("order")
                if order in orders:
                    errors.append(f"Duplicate stage order: {order}")
                orders.add(order)
                
                # Validate dependencies
                dependencies = stage.get("dependencies", [])
                for dep_order in dependencies:
                    if dep_order >= order:
                        errors.append(f"Stage {order} depends on later stage {dep_order}")
                    
                    if dep_order not in orders:
                        # Check if dependency exists in stages
                        dep_exists = any(s.get("order") == dep_order for s in stages)
                        if not dep_exists:
                            errors.append(f"Stage {order} depends on non-existent stage {dep_order}")
                
                # Validate skill name if provided
                if "skill" in stage:
                    skill = stage["skill"]
                    if not isinstance(skill, str) or not skill:
                        errors.append(f"Stage {order} has invalid skill name")
        
        # Validate quality gates
        if "quality_gates" in config:
            quality_gates = config["quality_gates"]
            
            if "test_coverage_threshold" in quality_gates:
                threshold = quality_gates["test_coverage_threshold"]
                if not (0 <= threshold <= 100):
                    errors.append(f"Test coverage threshold must be between 0 and 100: {threshold}")
        
        # Validate notification config
        if "notification_config" in config:
            notification_config = config["notification_config"]
            
            for event in ["on_success", "on_failure", "on_completion"]:
                if event in notification_config:
                    roles = notification_config[event]
                    if not isinstance(roles, list):
                        errors.append(f"{event} must be a list of roles")
        
        return errors
    
    def _validate_semantic_version(self, version: str) -> bool:
        """
        Validate semantic version format.
        
        Args:
            version: Version string to validate
            
        Returns:
            True if valid, False otherwise
        """
        import re
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))


def validate_config_file(config_path: Path, schema_dir: Optional[Path] = None) -> Tuple[int, str]:
    """
    Convenience function to validate a configuration file.
    
    Args:
        config_path: Path to the configuration file
        schema_dir: Directory containing schemas
        
    Returns:
        Tuple of (exit_code, output_message)
    """
    validator = ConfigValidator(schema_dir)
    
    # Determine config type based on file location
    if "pipeline" in str(config_path).lower():
        return validator.validate_pipeline_config(config_path)
    else:
        return validator.validate_skill_config(config_path)


def create_config_validator(schema_dir: Optional[Path] = None) -> ConfigValidator:
    """Create a config validator instance."""
    return ConfigValidator(schema_dir)