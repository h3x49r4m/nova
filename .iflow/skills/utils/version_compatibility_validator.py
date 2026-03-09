"""Version Compatibility Validator - Validates skill version compatibility.

This module provides functionality for validating that skill versions
are compatible with pipeline requirements and dependencies.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import (
    IFlowError,
    VersionError,
    ConfigError,
    ErrorCode,
    ErrorCategory
)


class VersionCompatibilityValidator:
    """Validates version compatibility between skills and pipelines."""
    
    def __init__(self, skills_dir: Path, schema_dir: Optional[Path] = None):
        """
        Initialize the version compatibility validator.
        
        Args:
            skills_dir: Directory containing all skills
            schema_dir: Directory containing schema files
        """
        self.skills_dir = skills_dir
        self.schema_dir = schema_dir
        self.skill_cache: Dict[str, Dict[str, Any]] = {}
    
    def _parse_version(self, version_str: str) -> Tuple[int, int, int]:
        """
        Parse semantic version string.
        
        Args:
            version_str: Version string (e.g., "1.2.3")
            
        Returns:
            Tuple of (major, minor, patch)
        """
        parts = version_str.split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two versions.
        
        Args:
            v1: First version string
            v2: Second version string
            
        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
        """
        v1_parts = self._parse_version(v1)
        v2_parts = self._parse_version(v2)
        
        if v1_parts < v2_parts:
            return -1
        elif v1_parts > v2_parts:
            return 1
        else:
            return 0
    
    def _check_version_requirement(
        self,
        current_version: str,
        required_version: str,
        operator: str = ">="
    ) -> bool:
        """
        Check if current version meets requirement.
        
        Args:
            current_version: Current version string
            required_version: Required version string
            operator: Comparison operator (>=, <=, ==, >, <)
            
        Returns:
            True if requirement is met
        """
        comparison = self._compare_versions(current_version, required_version)
        
        if operator == ">=":
            return comparison >= 0
        elif operator == "<=":
            return comparison <= 0
        elif operator == "==":
            return comparison == 0
        elif operator == ">":
            return comparison > 0
        elif operator == "<":
            return comparison < 0
        else:
            return False
    
    def _load_skill_config(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        Load skill configuration.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Skill configuration dictionary or None
        """
        if skill_name in self.skill_cache:
            return self.skill_cache[skill_name]
        
        skill_dir = self.skills_dir / skill_name
        config_file = skill_dir / "config.json"
        
        if not config_file.exists():
            return None
        
        try:
except Exception as e:
            self.logger.warning(f"Failed to load skill config for {skill_name}: {e}")
            return None
    
    def _load_skill_capabilities(
        self,
        skill_name: str,
        version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load skill capabilities for a specific version.
        
        Args:
            skill_name: Name of the skill
            version: Version to load (uses current if None)
            
        Returns:
            Capabilities dictionary or None
        """
        skill_config = self._load_skill_config(skill_name)
        
        if not skill_config:
            return None
        
        if version is None:
            version = skill_config.get("version", "1.0.0")
        
        capabilities_file = self.skills_dir / skill_name / "versions" / version / "capabilities.json"
        
        if not capabilities_file.exists():
            return None
        
        try:
            with open(capabilities_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load capabilities from {capabilities_file}: {e}")
            return None
    
    def validate_skill_version(
        self,
        skill_name: str,
        version: str
    ) -> Tuple[int, str]:
        """
        Validate that a skill version exists and is properly formatted.
        
        Args:
            skill_name: Name of the skill
            version: Version string to validate
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        # Validate version format
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            return 1, f"Invalid version format: {version}"
        
        # Check if skill exists
        skill_dir = self.skills_dir / skill_name
        if not skill_dir.exists():
            return 1, f"Skill not found: {skill_name}"
        
        # Check if version exists
        version_dir = skill_dir / "versions" / version
        if not version_dir.exists():
            return 1, f"Version {version} not found for skill {skill_name}"
        
        # Check capabilities file exists
        capabilities_file = version_dir / "capabilities.json"
        if not capabilities_file.exists():
            return 1, f"Capabilities file missing for {skill_name} version {version}"
        
        return 0, f"Skill {skill_name} version {version} is valid"
    
    def validate_pipeline_dependencies(
        self,
        pipeline_config: Dict[str, Any]
    ) -> Tuple[int, str, List[Dict[str, Any]]]:
        """
        Validate that all pipeline dependencies are satisfied.
        
        Args:
            pipeline_config: Pipeline configuration dictionary
            
        Returns:
            Tuple of (exit_code, output_message, dependency_results)
        """
        dependencies = pipeline_config.get("dependencies", {})
        results = []
        all_satisfied = True
        
        for skill_name, requirement in dependencies.items():
            result = {
                "skill": skill_name,
                "required": requirement,
                "satisfied": False,
                "current_version": None,
                "message": ""
            }
            
            # Load skill config
            skill_config = self._load_skill_config(skill_name)
            
            if not skill_config:
                result["message"] = f"Skill {skill_name} not found"
                all_satisfied = False
                results.append(result)
                continue
            
            current_version = skill_config.get("version", "1.0.0")
            result["current_version"] = current_version
            
            # Check if requirement is a simple version or has operator
            if isinstance(requirement, dict):
                min_version = requirement.get("min_version")
                max_version = requirement.get("max_version")
                
                if min_version and not self._check_version_requirement(current_version, min_version, ">="):
                    result["message"] = f"Current version {current_version} is less than required {min_version}"
                    all_satisfied = False
                elif max_version and not self._check_version_requirement(current_version, max_version, "<="):
                    result["message"] = f"Current version {current_version} is greater than allowed {max_version}"
                    all_satisfied = False
                else:
                    result["satisfied"] = True
                    result["message"] = f"Version {current_version} meets requirements"
            else:
                # Simple version requirement
                operator = ">="
                if not self._check_version_requirement(current_version, requirement, operator):
                    result["message"] = f"Current version {current_version} does not meet requirement {operator} {requirement}"
                    all_satisfied = False
                else:
                    result["satisfied"] = True
                    result["message"] = f"Version {current_version} meets requirement {operator} {requirement}"
            
            results.append(result)
        
        if all_satisfied:
            return 0, "All dependencies are satisfied", results
        else:
            failed_count = sum(1 for r in results if not r["satisfied"])
            return 1, f"{failed_count} dependency requirements not satisfied", results
    
    def validate_capability_compatibility(
        self,
        skill_name: str,
        required_capabilities: List[str]
    ) -> Tuple[int, str, List[str]]:
        """
        Validate that a skill has all required capabilities.
        
        Args:
            skill_name: Name of the skill
            required_capabilities: List of required capability names
            
        Returns:
            Tuple of (exit_code, output_message, missing_capabilities)
        """
        capabilities = self._load_skill_capabilities(skill_name)
        
        if not capabilities:
            return 1, f"Could not load capabilities for {skill_name}", required_capabilities
        
        available_capabilities = capabilities.get("capabilities", [])
        missing_capabilities = []
        
        for required in required_capabilities:
            if required not in available_capabilities:
                missing_capabilities.append(required)
        
        if not missing_capabilities:
            return 0, f"All required capabilities available in {skill_name}", []
        else:
            return 1, f"Missing capabilities in {skill_name}", missing_capabilities
    
    def validate_skill_pipeline_compatibility(
        self,
        skill_name: str,
        pipeline_type: str
    ) -> Tuple[int, str]:
        """
        Validate that a skill is compatible with a pipeline type.
        
        Args:
            skill_name: Name of the skill
            pipeline_type: Type of pipeline
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        capabilities = self._load_skill_capabilities(skill_name)
        
        if not capabilities:
            return 1, f"Could not load capabilities for {skill_name}"
        
        compatible_pipelines = capabilities.get("compatible_pipelines", [])
        
        if not compatible_pipelines:
            return 0, f"{skill_name} has no pipeline restrictions"
        
        if pipeline_type in compatible_pipelines or "*" in compatible_pipelines:
            return 0, f"{skill_name} is compatible with {pipeline_type}"
        else:
            return 1, f"{skill_name} is not compatible with {pipeline_type}. Compatible: {compatible_pipelines}"
    
    def get_available_versions(self, skill_name: str) -> List[str]:
        """
        Get all available versions for a skill.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            List of version strings sorted by version
        """
        skill_dir = self.skills_dir / skill_name
        versions_dir = skill_dir / "versions"
        
        if not versions_dir.exists():
            return []
        
        versions = []
        for version_dir in versions_dir.iterdir():
            if version_dir.is_dir():
                versions.append(version_dir.name)
        
        # Sort by version
        return sorted(versions, key=lambda v: self._parse_version(v))
    
    def get_latest_version(self, skill_name: str) -> Optional[str]:
        """
        Get the latest version of a skill.
        
        Args:
            skill_name: Name of the skill
            
        Returns:
            Latest version string or None
        """
        versions = self.get_available_versions(skill_name)
        return versions[-1] if versions else None
    
    def recommend_version(
        self,
        skill_name: str,
        requirement: Dict[str, Any]
    ) -> Optional[str]:
        """
        Recommend a version of a skill that meets requirements.
        
        Args:
            skill_name: Name of the skill
            requirement: Version requirement dictionary
            
        Returns:
            Recommended version or None
        """
        versions = self.get_available_versions(skill_name)
        
        if not versions:
            return None
        
        # Filter versions that meet requirements
        min_version = requirement.get("min_version")
        max_version = requirement.get("max_version")
        
        for version in reversed(versions):  # Check from newest to oldest
            if min_version and not self._check_version_requirement(version, min_version, ">="):
                continue
            if max_version and not self._check_version_requirement(version, max_version, "<="):
                continue
            return version
        
        return None


def create_version_compatibility_validator(
    skills_dir: Path,
    schema_dir: Optional[Path] = None
) -> VersionCompatibilityValidator:
    """Create a version compatibility validator instance."""
    return VersionCompatibilityValidator(
        skills_dir=skills_dir,
        schema_dir=schema_dir
    )