#!/usr/bin/env python3
"""Test suite for validating all config.json files.

This test validates all skill and pipeline configuration files against
the unified schema to ensure consistency and correctness.
"""

import json
from pathlib import Path
import pytest

from utils.skill_config_schema import SkillConfigValidator


class TestAllConfigFiles:
    """Tests for all config.json files in the skills directory."""

    @pytest.fixture
    def skills_dir(self):
        """Get the skills directory path."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def config_files(self, skills_dir):
        """Find all config.json files excluding version-specific ones."""
        all_configs = list(skills_dir.glob("**/config.json"))
        # Exclude version-specific config files as they have different schemas
        return [cfg for cfg in all_configs if "versions" not in cfg.parts]

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return SkillConfigValidator(strict=False)

    def test_config_files_exist(self, config_files):
        """Test that config.json files exist for all skills."""
        assert len(config_files) > 0, "No config.json files found"

    def test_all_configs_are_valid_json(self, config_files):
        """Test that all config.json files are valid JSON."""
        for config_file in config_files:
            try:
                with open(config_file, 'r') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {config_file}: {e}")

    def test_all_configs_validate_against_schema(self, config_files, validator):
        """Test that all config.json files validate against the unified schema."""
        errors_by_file = {}
        
        for config_file in config_files:
            is_valid, errors, config = validator.validate_file(config_file)
            if not is_valid:
                errors_by_file[str(config_file.relative_to(config_file.parent.parent))] = errors
        
        if errors_by_file:
            error_message = "Configuration validation failed:\n"
            for file_path, file_errors in errors_by_file.items():
                error_message += f"\n{file_path}:\n"
                for error in file_errors:
                    error_message += f"  - {error}\n"
            pytest.fail(error_message)

    def test_required_fields_present(self, config_files, validator):
        """Test that all configs have required fields."""
        required_fields = ["name", "version", "type", "description"]
        
        for config_file in config_files:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            for field in required_fields:
                assert field in config, f"{config_file.name}: Missing required field '{field}'"

    def test_version_format(self, config_files):
        """Test that all versions follow semantic versioning."""
        import re
        version_pattern = re.compile(r'^\d+\.\d+\.\d+$')
        
        for config_file in config_files:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            version = config.get("version")
            assert version is not None, f"{config_file.name}: Missing version"
            assert version_pattern.match(version), \
                f"{config_file.name}: Invalid version format '{version}'. Expected major.minor.patch"

    def test_name_format(self, config_files):
        """Test that all names follow the naming convention."""
        import re
        name_pattern = re.compile(r'^[a-z][a-z0-9-]*$')
        
        for config_file in config_files:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            name = config.get("name")
            assert name is not None, f"{config_file.name}: Missing name"
            assert name_pattern.match(name), \
                f"{config_file.name}: Invalid name format '{name}'. Must be lowercase, start with letter, contain only alphanumeric and hyphens"

    def test_type_is_valid(self, config_files):
        """Test that all type fields are valid."""
        valid_types = ["role", "pipeline"]
        
        for config_file in config_files:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            type_value = config.get("type")
            assert type_value is not None, f"{config_file.name}: Missing type"
            assert type_value in valid_types, \
                f"{config_file.name}: Invalid type '{type_value}'. Must be one of {valid_types}"

    def test_description_length(self, config_files):
        """Test that all descriptions meet minimum length requirements."""
        min_length = 10
        
        for config_file in config_files:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            description = config.get("description")
            assert description is not None, f"{config_file.name}: Missing description"
            assert len(description) >= min_length, \
                f"{config_file.name}: Description too short ({len(description)} chars). Minimum {min_length} chars required"

    def test_capabilities_is_array(self, config_files):
        """Test that capabilities field is an array if present."""
        for config_file in config_files:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            if "capabilities" in config:
                capabilities = config["capabilities"]
                assert isinstance(capabilities, list), \
                    f"{config_file.name}: capabilities must be an array"
                assert len(capabilities) > 0, \
                    f"{config_file.name}: capabilities array must have at least one item"

    def test_dependencies_format(self, config_files):
        """Test that dependencies are properly formatted if present."""
        for config_file in config_files:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            if "dependencies" in config:
                dependencies = config["dependencies"]
                assert isinstance(dependencies, list), \
                    f"{config_file.name}: dependencies must be an array"
                
                for i, dep in enumerate(dependencies):
                    assert isinstance(dep, dict), \
                        f"{config_file.name}: dependency at index {i} must be an object"
                    assert "name" in dep, \
                        f"{config_file.name}: dependency at index {i} missing 'name' field"
                    assert "min_version" in dep, \
                        f"{config_file.name}: dependency at index {i} missing 'min_version' field"

    def test_settings_structure(self, config_files):
        """Test that settings field has proper structure if present."""
        for config_file in config_files:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            if "settings" in config:
                settings = config["settings"]
                assert isinstance(settings, dict), \
                    f"{config_file.name}: settings must be an object"

    def test_config_name_matches_directory(self, config_files, skills_dir):
        """Test that config names match their directory names."""
        for config_file in config_files:
            # Skip version-specific configs
            if "versions" in config_file.parts:
                continue
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            config_name = config.get("name")
            directory_name = config_file.parent.name
            
            # Convert underscores to hyphens for comparison
            normalized_dir = directory_name.replace("_", "-")
            
            assert config_name is not None, f"{config_file.name}: Missing name"
            assert config_name == normalized_dir, \
                f"{config_file.name}: Config name '{config_name}' doesn't match directory name '{directory_name}'"

    def test_no_duplicate_names(self, config_files):
        """Test that all configs have unique names."""
        names = {}
        
        for config_file in config_files:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            name = config.get("name")
            if name in names:
                pytest.fail(
                    f"Duplicate name '{name}' found in {config_file.name} "
                    f"and {names[name]}"
                )
            names[name] = config_file.name

    def test_role_configs_have_role_type(self, config_files):
        """Test that role configs have type='role'."""
        role_directories = [
            "client", "product-manager", "project-manager", "tech-lead",
            "software-engineer", "testing-engineer", "qa-engineer",
            "devops-engineer", "security-engineer", "documentation-specialist",
            "ui-ux-designer", "git-manage", "git-flow"
        ]
        
        for config_file in config_files:
            # Check if this is a role directory
            if any(role_dir in str(config_file) for role_dir in role_directories):
                # Skip version-specific configs
                if "versions" in config_file.parts:
                    continue
                
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                assert config.get("type") == "role", \
                    f"{config_file.name}: Role config must have type='role'"

    def test_pipeline_configs_have_pipeline_type(self, config_files):
        """Test that pipeline configs have type='pipeline'."""
        for config_file in config_files:
            # Check if this is a pipeline directory
            if "team-pipeline-" in str(config_file):
                # Skip version-specific configs
                if "versions" in config_file.parts:
                    continue
                
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                assert config.get("type") == "pipeline", \
                    f"{config_file.name}: Pipeline config must have type='pipeline'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])