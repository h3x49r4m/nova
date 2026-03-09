"""Environment Configuration Loader - Loads configuration from environment variables.

This module provides functionality for loading and managing configuration
from environment variables with support for type conversion, defaults,
and validation.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from enum import Enum


class ConfigVarType(Enum):
    """Types of configuration variables."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    PATH = "path"
    JSON = "json"


class EnvironmentConfigLoader:
    """Loads configuration from environment variables."""
    
    def __init__(
        self,
        prefix: str = "IFLOW_",
        allow_override: bool = True,
        strict: bool = False
    ):
        """
        Initialize the environment config loader.
        
        Args:
            prefix: Prefix for environment variables
            allow_override: Whether to allow overriding existing config
            strict: Whether to require all variables to be defined
        """
        self.prefix = prefix
        self.allow_override = allow_override
        self.strict = strict
        self.config: Dict[str, Any] = {}
        self.variable_definitions: Dict[str, Dict[str, Any]] = {}
    
    def define_variable(
        self,
        name: str,
        var_type: ConfigVarType = ConfigVarType.STRING,
        default: Optional[Any] = None,
        required: bool = False,
        description: Optional[str] = None,
        choices: Optional[List[Any]] = None,
        validator: Optional[Callable[[Any], bool]] = None
    ):
        """
        Define a configuration variable.
        
        Args:
            name: Variable name (without prefix)
            var_type: Type of the variable
            default: Default value
            required: Whether the variable is required
            description: Description of the variable
            choices: List of valid choices
            validator: Custom validation function
        """
        self.variable_definitions[name] = {
            "type": var_type,
            "default": default,
            "required": required,
            "description": description,
            "choices": choices,
            "validator": validator
        }
    
    def define_variables(self, variables: Dict[str, Dict[str, Any]]):
        """
        Define multiple configuration variables.
        
        Args:
            variables: Dictionary of variable definitions
        """
        for name, definition in variables.items():
            self.define_variable(name, **definition)
    
    def _get_env_var_name(self, name: str) -> str:
        """Get the full environment variable name."""
        return f"{self.prefix}{name.upper()}"
    
    def _convert_value(
        self,
        value: str,
        var_type: ConfigVarType,
        name: str
    ) -> Any:
        """
        Convert string value to appropriate type.
        
        Args:
            value: String value from environment
            var_type: Target type
            name: Variable name for error messages
            
        Returns:
            Converted value
            
        Raises:
            ValueError: If conversion fails
        """
        try:
            if var_type == ConfigVarType.STRING:
                return value
            
            elif var_type == ConfigVarType.INTEGER:
                return int(value)
            
            elif var_type == ConfigVarType.FLOAT:
                return float(value)
            
            elif var_type == ConfigVarType.BOOLEAN:
                if value.lower() in ("true", "1", "yes", "on"):
                    return True
                elif value.lower() in ("false", "0", "no", "off"):
                    return False
                else:
                    raise ValueError(f"Invalid boolean value: {value}")
            
            elif var_type == ConfigVarType.LIST:
                # Split by comma and strip whitespace
                return [item.strip() for item in value.split(",")]
            
            elif var_type == ConfigVarType.PATH:
                return Path(value)
            
            elif var_type == ConfigVarType.JSON:
                import json
                return json.loads(value)
            
            else:
                return value
        
        except (ValueError, json.JSONDecodeError) as e:
            raise ValueError(
                f"Failed to convert {name} to {var_type.value}: {str(e)}"
            )
    
    def load(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Load configuration from environment variables.
        
        Args:
            config: Existing configuration to merge with
            
        Returns:
            Merged configuration dictionary
        """
        if config is None:
            config = {}
        
        result = config.copy() if config else {}
        
        # Load each defined variable
        for name, definition in self.variable_definitions.items():
            env_var_name = self._get_env_var_name(name)
            env_value = os.environ.get(env_var_name)
            
            if env_value is not None:
                # Convert and validate
                try:
                    value = self._convert_value(
                        env_value,
                        definition["type"],
                        name
                    )
                    
                    # Validate choices
                    if definition.get("choices") and value not in definition["choices"]:
                        raise ValueError(
                            f"Value '{value}' not in choices: {definition['choices']}"
                        )
                    
                    # Validate with custom validator
                    if definition.get("validator"):
                        if not definition["validator"](value):
                            raise ValueError(
                                f"Custom validation failed for {name}"
                            )
                    
                    # Set value
                    if self.allow_override or name not in result:
                        result[name] = value
                
                except ValueError as e:
                    if self.strict or definition.get("required", False):
                        raise ValueError(f"{env_var_name}: {str(e)}")
            
            elif definition.get("required", False) and name not in result:
                if self.strict:
                    raise ValueError(
                        f"Required environment variable {env_var_name} not set"
                    )
            
            elif name not in result and definition.get("default") is not None:
                # Use default value
                result[name] = definition["default"]
        
        self.config = result
        return result
    
    def get(self, name: str, default: Optional[Any] = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            name: Variable name
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(name, default)
    
    def get_int(self, name: str, default: Optional[int] = None) -> Optional[int]:
        """Get an integer configuration value."""
        value = self.get(name)
        if value is None:
            return default
        return int(value)
    
    def get_bool(self, name: str, default: Optional[bool] = None) -> Optional[bool]:
        """Get a boolean configuration value."""
        value = self.get(name)
        if value is None:
            return default
        return bool(value)
    
    def get_list(self, name: str, default: Optional[List[str]] = None) -> Optional[List[str]]:
        """Get a list configuration value."""
        value = self.get(name)
        if value is None:
            return default
        if isinstance(value, list):
            return value
        return [value]
    
    def get_path(self, name: str, default: Optional[Path] = None) -> Optional[Path]:
        """Get a path configuration value."""
        value = self.get(name)
        if value is None:
            return default
        if isinstance(value, Path):
            return value
        return Path(value)
    
    def set(self, name: str, value: Any):
        """
        Set a configuration value.
        
        Args:
            name: Variable name
            value: Value to set
        """
        self.config[name] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return self.config.copy()
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate current configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        for name, definition in self.variable_definitions.items():
            if definition.get("required", False) and name not in self.config:
                errors.append(f"Required variable '{name}' is not set")
                continue
            
            if name in self.config:
                value = self.config[name]
                
                # Validate type
                expected_type = definition["type"]
                if expected_type == ConfigVarType.INTEGER:
                    if not isinstance(value, int):
                        errors.append(f"'{name}' should be integer, got {type(value).__name__}")
                elif expected_type == ConfigVarType.FLOAT:
                    if not isinstance(value, (int, float)):
                        errors.append(f"'{name}' should be number, got {type(value).__name__}")
                elif expected_type == ConfigVarType.BOOLEAN:
                    if not isinstance(value, bool):
                        errors.append(f"'{name}' should be boolean, got {type(value).__name__}")
                elif expected_type == ConfigVarType.LIST:
                    if not isinstance(value, list):
                        errors.append(f"'{name}' should be list, got {type(value).__name__}")
                elif expected_type == ConfigVarType.PATH:
                    if not isinstance(value, (str, Path)):
                        errors.append(f"'{name}' should be path, got {type(value).__name__}")
                
                # Validate choices
                if definition.get("choices") and value not in definition["choices"]:
                    errors.append(
                        f"'{name}' value '{value}' not in choices: {definition['choices']}"
                    )
                
                # Validate with custom validator
                if definition.get("validator"):
                    if not definition["validator"](value):
                        errors.append(f"'{name}' failed custom validation")
        
        return len(errors) == 0, errors
    
    def get_help(self) -> str:
        """
        Get help text for all defined variables.
        
        Returns:
            Formatted help text
        """
        lines = ["Environment Configuration", "=" * 50, ""]
        lines.append(f"Prefix: {self.prefix}")
        lines.append("")
        
        for name, definition in self.variable_definitions.items():
            env_var_name = self._get_env_var_name(name)
            var_type = definition["type"].value
            default = definition.get("default", "none")
            required = definition.get("required", False)
            description = definition.get("description", "")
            choices = definition.get("choices")
            
            lines.append(f"{env_var_name}")
            lines.append(f"  Type: {var_type}")
            lines.append(f"  Default: {default}")
            lines.append(f"  Required: {'Yes' if required else 'No'}")
            
            if description:
                lines.append(f"  Description: {description}")
            
            if choices:
                lines.append(f"  Choices: {', '.join(str(c) for c in choices)}")
            
            lines.append("")
        
        return "\n".join(lines)


def create_env_config_loader(
    prefix: str = "IFLOW_",
    allow_override: bool = True,
    strict: bool = False
) -> EnvironmentConfigLoader:
    """Create an environment config loader instance."""
    return EnvironmentConfigLoader(prefix, allow_override, strict)


def load_config_from_env(
    config_file: Optional[Path] = None,
    prefix: str = "IFLOW_"
) -> Dict[str, Any]:
    """
    Load configuration from environment variables and optionally merge with file.
    
    Args:
        config_file: Optional path to config file
        prefix: Environment variable prefix
        
    Returns:
        Merged configuration
    """
    import json
    
    loader = create_env_config_loader(prefix=prefix)
    
    # Define common variables
    loader.define_variables({
        "log_level": {
            "type": ConfigVarType.STRING,
            "default": "INFO",
            "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "description": "Logging level"
        },
        "log_format": {
            "type": ConfigVarType.STRING,
            "default": "json",
            "choices": ["json", "text", "concise"],
            "description": "Log output format"
        },
        "dry_run": {
            "type": ConfigVarType.BOOLEAN,
            "default": False,
            "description": "Run in dry-run mode"
        },
        "repo_root": {
            "type": ConfigVarType.PATH,
            "description": "Repository root directory"
        },
        "max_retries": {
            "type": ConfigVarType.INTEGER,
            "default": 3,
            "description": "Maximum number of retries"
        },
        "timeout": {
            "type": ConfigVarType.INTEGER,
            "default": 120,
            "description": "Default timeout in seconds"
        }
    })
    
    # Load from file if provided
    file_config = {}
    if config_file and config_file.exists():
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    # Load from environment
    config = loader.load(file_config)
    
    return config
