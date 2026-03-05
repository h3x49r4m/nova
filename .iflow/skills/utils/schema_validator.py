#!/usr/bin/env python3
"""
JSON Schema Validator
Validates state files against JSON schemas to ensure data integrity.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class SchemaValidationError(Exception):
    """Exception raised when schema validation fails."""
    def __init__(self, message: str, errors: List[str]):
        self.message = message
        self.errors = errors
        super().__init__(self.message)


class SchemaValidator:
    """
    Validates data against JSON schemas.
    
    This is a lightweight validator that doesn't require external dependencies.
    For production use, consider using jsonschema library.
    """
    
    def __init__(self, schema_dir: Optional[Path] = None):
        """
        Initialize schema validator.
        
        Args:
            schema_dir: Directory containing schema files
        """
        self.schema_dir = schema_dir
        self._schema_cache: Dict[str, Dict] = {}
    
    def load_schema(self, schema_name: str) -> Optional[Dict]:
        """
        Load a schema from file or cache.
        
        Args:
            schema_name: Name of the schema file (without .json extension)
            
        Returns:
            Schema dictionary or None if not found
        """
        if schema_name in self._schema_cache:
            return self._schema_cache[schema_name]
        
        if self.schema_dir is None:
            return None
        
        schema_file = self.schema_dir / f'{schema_name}.json'
        if not schema_file.exists():
            return None
        
        try:
            with open(schema_file, 'r') as f:
                schema = json.load(f)
                self._schema_cache[schema_name] = schema
                return schema
        except (json.JSONDecodeError, IOError):
            return None
    
    def validate(self, data: Dict, schema_name: str) -> Tuple[bool, List[str]]:
        """
        Validate data against a schema.
        
        Args:
            data: Data to validate
            schema_name: Name of schema to validate against
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        schema = self.load_schema(schema_name)
        
        if schema is None:
            return False, [f'Schema "{schema_name}" not found']
        
        errors: List[str] = []
        
        # Check required fields
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in data:
                errors.append(f'Missing required field: {field}')
        
        # Validate each field according to schema
        properties = schema.get('properties', {})
        for field_name, field_schema in properties.items():
            if field_name not in data:
                continue
            
            field_value = data[field_name]
            field_errors = self._validate_field(field_value, field_schema, field_name)
            errors.extend(field_errors)
        
        # Validate additional properties if specified
        if 'additionalProperties' in schema and not schema['additionalProperties']:
            allowed_fields = set(properties.keys())
            for field_name in data.keys():
                if field_name not in allowed_fields:
                    errors.append(f'Unexpected field: {field_name}')
        
        return len(errors) == 0, errors
    
    def _validate_field(self, value: any, field_schema: Dict, field_path: str = '') -> List[str]:
        """
        Validate a single field value against its schema.
        
        Args:
            value: Value to validate
            field_schema: Schema for this field
            field_path: Path to this field (for error messages)
            
        Returns:
            List of error messages
        """
        errors: List[str] = []
        prefix = f'{field_path}: ' if field_path else ''
        
        # Check type
        expected_type = field_schema.get('type')
        if expected_type and not self._check_type(value, expected_type):
            errors.append(f'{prefix}Expected type {expected_type}, got {type(value).__name__}')
            return errors
        
        # Check enum values
        if 'enum' in field_schema and value not in field_schema['enum']:
            errors.append(f'{prefix}Value must be one of {field_schema["enum"]}, got {value}')
        
        # Check minimum/maximum for numbers
        if isinstance(value, (int, float)):
            if 'minimum' in field_schema and value < field_schema['minimum']:
                errors.append(f'{prefix}Value {value} is less than minimum {field_schema["minimum"]}')
            if 'maximum' in field_schema and value > field_schema['maximum']:
                errors.append(f'{prefix}Value {value} is greater than maximum {field_schema["maximum"]}')
        
        # Check min/max length for strings and arrays
        if isinstance(value, (str, list)):
            if 'minLength' in field_schema and len(value) < field_schema['minLength']:
                errors.append(f'{prefix}Length {len(value)} is less than minimum {field_schema["minLength"]}')
            if 'maxLength' in field_schema and len(value) > field_schema['maxLength']:
                errors.append(f'{prefix}Length {len(value)} is greater than maximum {field_schema["maxLength"]}')
        
        # Check pattern for strings
        if isinstance(value, str) and 'pattern' in field_schema:
            import re
            if not re.match(field_schema['pattern'], value):
                errors.append(f'{prefix}Value does not match required pattern')
        
        # Validate array items
        if isinstance(value, list) and 'items' in field_schema:
            items_schema = field_schema['items']
            if isinstance(items_schema, dict):
                # Validate all items against the same schema
                for i, item in enumerate(value):
                    item_errors = self._validate_field(item, items_schema, f'{field_path}[{i}]')
                    errors.extend(item_errors)
        
        # Validate nested objects
        if isinstance(value, dict):
            # Check required fields in nested object
            nested_required = field_schema.get('required', [])
            for nested_field in nested_required:
                if nested_field not in value:
                    errors.append(f'{prefix}Missing required nested field: {nested_field}')
            
            # Validate nested properties
            nested_properties = field_schema.get('properties', {})
            for nested_field, nested_value in value.items():
                if nested_field in nested_properties:
                    nested_errors = self._validate_field(
                        nested_value,
                        nested_properties[nested_field],
                        f'{field_path}.{nested_field}'
                    )
                    errors.extend(nested_errors)
        
        return errors
    
    def _check_type(self, value: any, expected_type: str) -> bool:
        """
        Check if value matches expected type.
        
        Args:
            value: Value to check
            expected_type: Expected type string
            
        Returns:
            True if type matches
        """
        type_map = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict,
            'null': type(None)
        }
        
        if expected_type in type_map:
            return isinstance(value, type_map[expected_type])
        
        # Handle union types (e.g., ["string", "null"])
        if isinstance(expected_type, list):
            return any(self._check_type(value, t) for t in expected_type)
        
        return True


def validate_workflow_state(data: Dict, schema_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate workflow state.
    
    Args:
        data: Workflow state data
        schema_dir: Directory containing schemas
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = SchemaValidator(schema_dir)
    return validator.validate(data, 'workflow-state')


def validate_branch_state(data: Dict, schema_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate branch state.
    
    Args:
        data: Branch state data
        schema_dir: Directory containing schemas
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = SchemaValidator(schema_dir)
    return validator.validate(data, 'branch-state')


def validate_pipeline_state(data: Dict, schema_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate pipeline state.
    
    Args:
        data: Pipeline state data
        schema_dir: Directory containing schemas
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = SchemaValidator(schema_dir)
    return validator.validate(data, 'pipeline-state')


def validate_json_schema(data: Dict, schema_path: Path) -> Tuple[bool, List[str]]:
    """
    Validate data against a JSON schema file.
    
    Args:
        data: Data to validate
        schema_path: Path to the schema file
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    schema_dir = schema_path.parent if schema_path.parent.name == 'schemas' else schema_path.parent.parent / 'schemas'
    schema_name = schema_path.stem
    
    validator = SchemaValidator(schema_dir)
    return validator.validate(data, schema_name)