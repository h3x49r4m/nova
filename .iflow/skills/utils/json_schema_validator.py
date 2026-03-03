"""JSON Schema Validator - Validates JSON files against JSON schemas.

This module provides functionality for validating JSON configuration files
against JSON Schema specifications, ensuring data integrity and correctness.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re

from .exceptions import IFlowError, ErrorCode, ValidationError


class ValidationErrorType(Enum):
    """Types of validation errors."""
    TYPE_MISMATCH = "type_mismatch"
    REQUIRED_MISSING = "required_missing"
    ADDITIONAL_PROPERTIES = "additional_properties"
    PATTERN_MISMATCH = "pattern_mismatch"
    ENUM_MISMATCH = "enum_mismatch"
    RANGE_VIOLATION = "range_violation"
    FORMAT_INVALID = "format_invalid"
    UNIQUE_ITEMS = "unique_items"
    MIN_ITEMS = "min_items"
    MAX_ITEMS = "max_items"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    DEPENDENCY_FAILED = "dependency_failed"
    REF_NOT_FOUND = "ref_not_found"


class SchemaValidationError(Exception):
    """Exception raised when schema validation fails."""
    
    def __init__(self, message: str, path: str = "", error_type: Optional[ValidationErrorType] = None):
        """
        Initialize schema validation error.
        
        Args:
            message: Error message
            path: JSON path to the invalid value
            error_type: Type of validation error
        """
        super().__init__(message)
        self.path = path
        self.error_type = error_type


class JSONSchemaValidator:
    """Validates JSON data against JSON schemas."""
    
    def __init__(self, schema_dir: Optional[Path] = None):
        """
        Initialize the JSON schema validator.
        
        Args:
            schema_dir: Directory containing schema files
        """
        self.schema_dir = schema_dir or Path(".iflow/schemas")
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self._load_schemas()
    
    def _load_schemas(self):
        """Load all schemas from the schema directory."""
        if not self.schema_dir.exists():
            return
        
        for schema_file in self.schema_dir.glob("*.json"):
            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                    schema_name = schema_file.stem
                    self.schemas[schema_name] = schema
            except (json.JSONDecodeError, IOError):
                pass
    
    def load_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a schema by name.
        
        Args:
            schema_name: Name of the schema
            
        Returns:
            Schema dictionary or None if not found
        """
        if schema_name in self.schemas:
            return self.schemas[schema_name]
        
        # Try loading from file
        schema_file = self.schema_dir / f"{schema_name}.json"
        if schema_file.exists():
            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                    self.schemas[schema_name] = schema
                    return schema
            except (json.JSONDecodeError, IOError):
                pass
        
        return None
    
    def validate(
        self,
        data: Dict[str, Any],
        schema_name: str,
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate data against a schema.
        
        Args:
            data: Data to validate
            schema_name: Name of the schema
            schema: Optional schema dictionary (if not using schema_name)
            
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []
        
        # Load schema if not provided
        if schema is None:
            schema = self.load_schema(schema_name)
            if not schema:
                return False, [f"Schema '{schema_name}' not found"]
        
        # Validate against schema
        try:
            self._validate_recursive(data, schema, "", errors)
        except SchemaValidationError as e:
            errors.append(f"{e.path}: {str(e)}")
        
        return len(errors) == 0, errors
    
    def _validate_recursive(
        self,
        data: Any,
        schema: Dict[str, Any],
        path: str,
        errors: List[str]
    ):
        """
        Recursively validate data against schema.
        
        Args:
            data: Data to validate
            schema: Schema to validate against
            path: Current JSON path
            errors: List to collect errors
        """
        # Handle $ref
        if "$ref" in schema:
            ref_path = schema["$ref"]
            ref_schema = self._resolve_ref(ref_path)
            if ref_schema:
                self._validate_recursive(data, ref_schema, path, errors)
            else:
                errors.append(f"{path}: Reference '{ref_path}' not found")
            return
        
        # Check type
        if "type" in schema:
            type_errors = self._validate_type(data, schema["type"], path)
            errors.extend(type_errors)
            if type_errors:
                return
        
        # Check enum
        if "enum" in schema:
            if data not in schema["enum"]:
                errors.append(
                    f"{path}: Value '{data}' must be one of {schema['enum']}"
                )
                return
        
        # Check required (for objects)
        if "required" in schema and isinstance(data, dict):
            for required_field in schema["required"]:
                if required_field not in data:
                    errors.append(
                        f"{path}.{required_field}: Required field missing"
                    )
        
        # Check properties (for objects)
        if "properties" in schema and isinstance(data, dict):
            for prop_name, prop_schema in schema["properties"].items():
                if prop_name in data:
                    prop_path = f"{path}.{prop_name}" if path else prop_name
                    self._validate_recursive(data[prop_name], prop_schema, prop_path, errors)
            
            # Check additionalProperties
            additional_props = schema.get("additionalProperties", True)
            if isinstance(additional_props, bool) and not additional_props:
                allowed_props = set(schema["properties"].keys())
                for prop_name in data.keys():
                    if prop_name not in allowed_props:
                        errors.append(
                            f"{path}.{prop_name}: Additional property not allowed"
                        )
        
        # Check items (for arrays)
        if "items" in schema and isinstance(data, list):
            for i, item in enumerate(data):
                item_path = f"{path}[{i}]"
                self._validate_recursive(item, schema["items"], item_path, errors)
        
        # Check array constraints
        if isinstance(data, list):
            if "minItems" in schema and len(data) < schema["minItems"]:
                errors.append(
                    f"{path}: Array must have at least {schema['minItems']} items"
                )
            
            if "maxItems" in schema and len(data) > schema["maxItems"]:
                errors.append(
                    f"{path}: Array must have at most {schema['maxItems']} items"
                )
            
            if schema.get("uniqueItems", False):
                if len(data) != len(set(json.dumps(item) for item in data)):
                    errors.append(f"{path}: Array items must be unique")
        
        # Check string constraints
        if isinstance(data, str):
            if "minLength" in schema and len(data) < schema["minLength"]:
                errors.append(
                    f"{path}: String must be at least {schema['minLength']} characters"
                )
            
            if "maxLength" in schema and len(data) > schema["maxLength"]:
                errors.append(
                    f"{path}: String must be at most {schema['maxLength']} characters"
                )
            
            if "pattern" in schema:
                pattern = schema["pattern"]
                if not re.match(pattern, data):
                    errors.append(
                        f"{path}: String does not match pattern '{pattern}'"
                    )
            
            if "format" in schema:
                format_errors = self._validate_format(data, schema["format"], path)
                errors.extend(format_errors)
        
        # Check numeric constraints
        if isinstance(data, (int, float)):
            if "minimum" in schema and data < schema["minimum"]:
                errors.append(
                    f"{path}: Value must be at least {schema['minimum']}"
                )
            
            if "maximum" in schema and data > schema["maximum"]:
                errors.append(
                    f"{path}: Value must be at most {schema['maximum']}"
                )
            
            if "exclusiveMinimum" in schema and data <= schema["exclusiveMinimum"]:
                errors.append(
                    f"{path}: Value must be greater than {schema['exclusiveMinimum']}"
                )
            
            if "exclusiveMaximum" in schema and data >= schema["exclusiveMaximum"]:
                errors.append(
                    f"{path}: Value must be less than {schema['exclusiveMaximum']}"
                )
        
        # Check dependencies
        if "dependencies" in schema and isinstance(data, dict):
            for dep_field, dep_value in schema["dependencies"].items():
                if dep_field in data:
                    if isinstance(dep_value, list):
                        # Property dependencies
                        for required_field in dep_value:
                            if required_field not in data:
                                errors.append(
                                    f"{path}: Field '{dep_field}' requires '{required_field}'"
                                )
                    elif isinstance(dep_value, dict):
                        # Schema dependencies
                        self._validate_recursive(data, dep_value, path, errors)
    
    def _validate_type(
        self,
        data: Any,
        type_spec: Any,
        path: str
    ) -> List[str]:
        """
        Validate data type.
        
        Args:
            data: Data to validate
            type_spec: Type specification from schema
            path: Current JSON path
            
        Returns:
            List of error messages
        """
        errors = []
        
        if isinstance(type_spec, str):
            types = [type_spec]
        else:
            types = type_spec
        
        valid = False
        
        for type_name in types:
            if type_name == "string" and isinstance(data, str):
                valid = True
            elif type_name == "number" and isinstance(data, (int, float)) and not isinstance(data, bool):
                valid = True
            elif type_name == "integer" and isinstance(data, int) and not isinstance(data, bool):
                valid = True
            elif type_name == "boolean" and isinstance(data, bool):
                valid = True
            elif type_name == "array" and isinstance(data, list):
                valid = True
            elif type_name == "object" and isinstance(data, dict):
                valid = True
            elif type_name == "null" and data is None:
                valid = True
        
        if not valid:
            errors.append(
                f"{path}: Expected type {types}, got {type(data).__name__}"
            )
        
        return errors
    
    def _validate_format(
        self,
        data: str,
        format_name: str,
        path: str
    ) -> List[str]:
        """
        Validate string format.
        
        Args:
            data: String to validate
            format_name: Format name
            path: Current JSON path
            
        Returns:
            List of error messages
        """
        errors = []
        
        format_patterns = {
            "uri": r'^[a-zA-Z][a-zA-Z0-9+.-]*://',
            "uri-reference": r'^[a-zA-Z][a-zA-Z0-9+.-]*://',
            "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            "ipv4": r'^(\d{1,3}\.){3}\d{1,3}$',
            "ipv6": r'^[0-9a-fA-F:]+$',
            "date-time": r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
            "date": r'^\d{4}-\d{2}-\d{2}$',
            "time": r'^\d{2}:\d{2}:\d{2}',
            "uuid": r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        }
        
        if format_name in format_patterns:
            pattern = format_patterns[format_name]
            if not re.match(pattern, data):
                errors.append(
                    f"{path}: Value does not match format '{format_name}'"
                )
        
        return errors
    
    def _resolve_ref(self, ref_path: str) -> Optional[Dict[str, Any]]:
        """
        Resolve a $ref reference.
        
        Args:
            ref_path: Reference path (e.g., "#/definitions/foo")
            
        Returns:
            Resolved schema or None
        """
        if ref_path.startswith("#/"):
            # Internal reference
            parts = ref_path[2:].split("/")
            current = self.schemas.get(parts[0], {})
            
            for part in parts[1:]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            
            return current if isinstance(current, dict) else None
        
        return None
    
    def get_available_schemas(self) -> List[str]:
        """Get list of available schema names."""
        return list(self.schemas.keys())
    
    def validate_file(
        self,
        file_path: Path,
        schema_name: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate a JSON file against a schema.
        
        Args:
            file_path: Path to JSON file
            schema_name: Name of schema to validate against
            
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            return self.validate(data, schema_name)
        
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {str(e)}"]
        except IOError as e:
            return False, [f"Failed to read file: {str(e)}"]


def create_json_schema_validator(
    schema_dir: Optional[Path] = None
) -> JSONSchemaValidator:
    """Create a JSON schema validator instance."""
    return JSONSchemaValidator(schema_dir)