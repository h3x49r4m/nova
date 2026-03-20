#!/usr/bin/env python3
"""
Skill Version Manager
Manages skill versioning, capabilities, and compatibility with pipelines.
"""

import importlib.util
import json
from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

try:
    from .utils.structured_logger import StructuredLogger, get_logger
except ImportError:
    from utils.structured_logger import StructuredLogger, get_logger


class SkillVersionManager:
    """Manages versioning for individual skills."""

    def __init__(self, skill_name: str, skills_dir: Path):
        self.skill_name = skill_name
        self.skill_dir = skills_dir / skill_name
        self.versions_dir = self.skill_dir / 'versions'
        self.config_file = self.skill_dir / 'config.json'
        self.logger = get_logger(f"skill.{skill_name}")

        self.current_version = self.load_current_version()
        self.available_versions = self.load_available_versions()
        self.capabilities = self.load_capabilities()

    def load_current_version(self) -> str:
        """Load current skill version from config."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
                    return config.get('version', '1.0.0')
            except (OSError, json.JSONDecodeError):
                pass
        return '1.0.0'

    def load_available_versions(self) -> list[str]:
        """Load all available skill versions."""
        versions = []
        if self.versions_dir.exists():
            for version_dir in self.versions_dir.iterdir():
                if version_dir.is_dir():
                    versions.append(version_dir.name)
        return sorted(versions, key=self._parse_version)

    def load_capabilities(self) -> dict[str, dict]:
        """Load capabilities for all versions."""
        capabilities = {}

        if not self.versions_dir.exists():
            return capabilities

        for version_dir in self.versions_dir.iterdir():
            if not version_dir.is_dir():
                continue

            version = version_dir.name
            capabilities_file = version_dir / 'capabilities.json'

            if capabilities_file.exists():
                with open(capabilities_file) as f:
                    capabilities[version] = json.load(f)

        return capabilities

    def _parse_version(self, version_str: str) -> tuple[int, int, int]:
        """Parse semantic version string."""
        parts = version_str.split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)

    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two versions. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
        v1_parts = self._parse_version(v1)
        v2_parts = self._parse_version(v2)

        if v1_parts < v2_parts:
            return -1
        elif v1_parts > v2_parts:
            return 1
        else:
            return 0

    def get_capabilities(self, version: str) -> dict | None:
        """Get capabilities for a specific version."""
        return self.capabilities.get(version)

    def check_version_compatibility(self, required_version: str, operator: str = ">=") -> bool:
        """Check if current version meets requirement."""
        comparison = self._compare_versions(self.current_version, required_version)
        if operator == ">=":
            return comparison >= 0
        elif operator == "==":
            return comparison == 0
        elif operator == "<=":
            return comparison <= 0
        elif operator == ">":
            return comparison > 0
        elif operator == "<":
            return comparison < 0
        return False

    def find_compatible_version(self, min_version: str | None = None,
                               max_version: str | None = None) -> str | None:
        """Find a compatible version within range."""
        candidates = self.available_versions

        if min_version:
            candidates = [v for v in candidates if self._compare_versions(v, min_version) >= 0]

        if max_version:
            candidates = [v for v in candidates if self._compare_versions(v, max_version) <= 0]

        if not candidates:
            return None

        # Return the latest compatible version
        return max(candidates, key=self._parse_version)

    def get_version_info(self, version: str) -> dict | None:
        """Get detailed info about a version."""
        version_dir = self.versions_dir / version
        if not version_dir.exists():
            return None

        info = {
            'version': version,
            'capabilities': self.capabilities.get(version, {}),
            'breaking_changes': []
        }

        # Load breaking changes
        breaking_file = version_dir / 'breaking_changes.json'
        if breaking_file.exists():
            with open(breaking_file) as f:
                info['breaking_changes'] = json.load(f)

        return info

    def get_migration(self, from_version: str, to_version: str) -> Callable | None:
        """
        Load a migration function from a migration file.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            Migration function or None if not found
        """
        migration_dir = self.versions_dir / to_version / 'migrations'
        if not migration_dir.exists():
            return None

        migration_file = migration_dir / f'from_{from_version.replace(".", "_")}.py'
        if not migration_file.exists():
            return None

        try:
            spec = importlib.util.spec_from_file_location(f"migration_{migration_file.stem}", migration_file)
            if spec is None or spec.loader is None:
                self.logger.warning(
                    f"Could not load migration from {migration_file}",
                    extra={
                        "file": str(migration_file),
                        "from_version": from_version,
                        "to_version": to_version
                    }
                )
                return None

            migration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration_module)

            # Look for migrate or migrate_state function
            if hasattr(migration_module, 'migrate'):
                return migration_module.migrate
            elif hasattr(migration_module, 'migrate_state'):
                return migration_module.migrate_state
        except Exception as e:
            self.logger.warning(
                f"Failed to load migration function from {migration_file}: {e}",
                extra={
                    "file": str(migration_file),
                    "error_type": type(e).__name__,
                    "from_version": from_version,
                    "to_version": to_version
                }
            )

        return None

    def execute_migration(self, state: dict, from_version: str, to_version: str) -> tuple[bool, dict | str]:
        """
        Execute a migration from one version to another.

        Args:
            state: Current state dictionary
            from_version: Source version
            to_version: Target version

        Returns:
            Tuple of (success, result) where result is new state dict on success or error message on failure
        """
        migration_func = self.get_migration(from_version, to_version)

        if migration_func is None:
            return False, f"No migration found from {from_version} to {to_version}"

        try:
            # Execute migration
            new_state = migration_func(deepcopy(state))

            # Validate migration output
            if not isinstance(new_state, dict):
                return False, "Migration function must return a dictionary"

            return True, new_state
        except Exception as e:
            return False, f"Migration failed: {e!s}"

    def get_migration_path(self, from_version: str, to_version: str) -> list[str]:
        """
        Get the path of versions to migrate through.

        Args:
            from_version: Starting version
            to_version: Target version

        Returns:
            List of version strings to migrate through

        Raises:
            ValueError: If no migration path exists
        """
        if self._compare_versions(from_version, to_version) >= 0:
            raise ValueError(f"Target version {to_version} is not newer than {from_version}")

        path: list[str] = []
        current = from_version

        while self._compare_versions(current, to_version) < 0:
            # Find next version
            next_versions = [
                v for v in self.available_versions
                if self._compare_versions(v, current) > 0
            ]

            if not next_versions:
                raise ValueError(f"No migration path from {current} to {to_version}")

            # Get the closest next version
            next_version = min(next_versions, key=lambda v: self._parse_version(v))

            # Check if migration exists
            if self.get_migration(current, next_version) is None:
                raise ValueError(f"No migration from {current} to {next_version}")

            path.append(next_version)
            current = next_version

        return path


class SkillRegistry:
    """Central registry for all skills and their versions."""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: dict[str, SkillVersionManager] = {}
        self.load_all_skills()

    def load_all_skills(self):
        """Load all available skills."""
        if not self.skills_dir.exists():
            return

        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_name = skill_dir.name
            # Skip if not a skill (no SKILL.md or config.json)
            if not (skill_dir / 'SKILL.md').exists() and not (skill_dir / 'config.json').exists():
                continue

            self.skills[skill_name] = SkillVersionManager(skill_name, self.skills_dir)

    def get_skill(self, skill_name: str) -> SkillVersionManager | None:
        """Get a skill manager by name."""
        return self.skills.get(skill_name)

    def list_skills(self) -> list[str]:
        """List all available skills."""
        return sorted(self.skills.keys())

    def get_skill_capabilities(self, skill_name: str, version: str) -> dict | None:
        """Get capabilities for a specific skill version."""
        skill = self.get_skill(skill_name)
        if skill:
            return skill.get_capabilities(version)
        return None

    def find_skill_for_capability(self, capability: str, min_version: str | None = None) -> list[tuple[str, str]]:
        """Find skills that provide a specific capability."""
        results = []

        for skill_name, skill in self.skills.items():
            for version, caps in skill.capabilities.items():
                if capability in caps.get('capabilities', []):
                    if min_version is None or skill._compare_versions(version, min_version) >= 0:
                        results.append((skill_name, version))

        return results

    def get_compatibility_matrix(self) -> dict[str, dict[str, list[str]]]:
        """Get compatibility matrix for all skills."""
        matrix = {}

        for skill_name, skill in self.skills.items():
            matrix[skill_name] = {}
            for version, caps in skill.capabilities.items():
                matrix[skill_name][version] = caps.get('compatible_pipelines', ['*'])

        return matrix


class SkillDependencyResolver:
    """Resolves skill version requirements and dependencies."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def resolve_pipeline_requirements(self, pipeline_config: dict) -> tuple[bool, dict[str, str], list[str]]:
        """
        Resolve skill versions required by a pipeline.
        Returns (success, skill_versions, errors)
        """
        skill_versions = {}
        errors = []

        skills_config = pipeline_config.get('skills', {})

        for skill_name, skill_req in skills_config.items():
            skill = self.registry.get_skill(skill_name)

            if not skill:
                errors.append(f"Skill '{skill_name}' not found")
                continue

            min_version = skill_req.get('min_version')
            max_version = skill_req.get('max_version')
            preferred_version = skill_req.get('version')

            # Try preferred version first
            if preferred_version:
                if preferred_version in skill.available_versions:
                    skill_versions[skill_name] = preferred_version
                    continue
                else:
                    errors.append(f"Preferred version {preferred_version} not available for {skill_name}")

            # Find compatible version
            compatible = skill.find_compatible_version(min_version, max_version)

            if compatible:
                skill_versions[skill_name] = compatible
            else:
                errors.append(f"No compatible version found for {skill_name} (min: {min_version}, max: {max_version})")

        # Check skill dependencies
        dependency_errors = self._check_skill_dependencies(skill_versions)
        errors.extend(dependency_errors)

        return (len(errors) == 0, skill_versions, errors)

    def _check_skill_dependencies(self, skill_versions: dict[str, str]) -> list[str]:
        """Check if selected skill versions have compatible dependencies."""
        errors = []

        for skill_name, version in skill_versions.items():
            skill = self.registry.get_skill(skill_name)
            if not skill:
                continue

            capabilities = skill.get_capabilities(version)
            if not capabilities:
                continue

            dependencies = capabilities.get('dependencies', {})

            for dep_skill, dep_req in dependencies.items():
                if dep_skill not in skill_versions:
                    errors.append(f"{skill_name}@{version} requires {dep_skill}")
                    continue

                dep_version = skill_versions[dep_skill]
                dep_manager = self.registry.get_skill(dep_skill)

                if not dep_manager:
                    continue

                min_version = dep_req.get('min_version')
                if min_version and dep_manager._compare_versions(dep_version, min_version) < 0:
                    errors.append(f"{skill_name}@{version} requires {dep_skill}>={min_version}, but {dep_version} is selected")

        return errors

    def validate_workflow_state_compatibility(self, workflow_state: dict) -> tuple[bool, list[str]]:
        """Validate if workflow state is compatible with current skill versions."""
        errors = []

        skills_used = workflow_state.get('skills_used', {})

        for skill_name, version in skills_used.items():
            skill = self.registry.get_skill(skill_name)

            if not skill:
                errors.append(f"Skill {skill_name}@{version} no longer exists")
                continue

            if version not in skill.available_versions:
                errors.append(f"Version {version} of {skill_name} no longer available")

        return (len(errors) == 0, errors)

    def suggest_upgrade_path(self, current_versions: dict[str, str],
                           target_requirements: dict[str, str]) -> dict[str, str] | None:
        """
        Suggest an upgrade path from current to target versions.
        Returns None if upgrade not possible.
        """
        upgrade_path = {}

        for skill_name, target_version in target_requirements.items():
            current_version = current_versions.get(skill_name)
            skill = self.registry.get_skill(skill_name)

            if not skill:
                return None

            # If no current version, use target
            if not current_version:
                upgrade_path[skill_name] = target_version
                continue

            # Check if upgrade needed
            if skill._compare_versions(target_version, current_version) > 0:
                # Check if upgrade path exists (through intermediate versions)
                available = skill.available_versions
                if current_version in available and target_version in available:
                    upgrade_path[skill_name] = target_version
                else:
                    return None
            else:
                # Already at or past target version
                upgrade_path[skill_name] = current_version

        return upgrade_path


class SkillCompatibilityChecker:
    """Checks compatibility between skills and pipelines."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def check_pipeline_compatibility(self, pipeline_name: str, pipeline_config: dict) -> tuple[bool, list[str]]:
        """Check if pipeline is compatible with available skills."""
        errors = []

        # Check required skills
        skills_config = pipeline_config.get('skills', {})

        for skill_name, skill_req in skills_config.items():
            skill = self.registry.get_skill(skill_name)

            if not skill:
                errors.append(f"Required skill '{skill_name}' not installed")
                continue

            # Check version requirements
            min_version = skill_req.get('min_version')
            max_version = skill_req.get('max_version')

            if min_version and skill.current_version and skill._compare_versions(skill.current_version, min_version) < 0:
                errors.append(f"{skill_name} requires version >= {min_version}, but {skill.current_version} is installed")

            if max_version and skill.current_version and skill._compare_versions(skill.current_version, max_version) > 0:
                errors.append(f"{skill_name} requires version <= {max_version}, but {skill.current_version} is installed")

        # Check skill capabilities match pipeline needs
        required_capabilities = pipeline_config.get('required_capabilities', [])

        for capability in required_capabilities:
            skills_with_capability = self.registry.find_skill_for_capability(capability)
            if not skills_with_capability:
                errors.append(f"No skill provides required capability: {capability}")

        return (len(errors) == 0, errors)

    def check_skill_breaking_changes(self, skill_name: str, from_version: str, to_version: str) -> list[str]:
        """Check for breaking changes between skill versions."""
        skill = self.registry.get_skill(skill_name)
        if not skill:
            return [f"Skill {skill_name} not found"]

        from_info = skill.get_version_info(from_version)
        to_info = skill.get_version_info(to_version)

        if not from_info or not to_info:
            return ["One or both versions not found"]

        # Get breaking changes from all versions between from and to
        breaking_changes = []

        for version in skill.available_versions:
            if skill._compare_versions(version, from_version) > 0 and skill._compare_versions(version, to_version) <= 0:
                version_info = skill.get_version_info(version)
                if version_info:
                    breaking_changes.extend(version_info.get('breaking_changes', []))

        return breaking_changes

    def generate_compatibility_report(self, pipeline_config: dict) -> dict:
        """Generate a comprehensive compatibility report."""
        report = {
            'pipeline': pipeline_config.get('pipeline', 'unknown'),
            'compatible': True,
            'skills': {},
            'warnings': [],
            'errors': []
        }

        skills_config = pipeline_config.get('skills', {})

        for skill_name, skill_req in skills_config.items():
            skill = self.registry.get_skill(skill_name)

            if not skill:
                report['skills'][skill_name] = {
                    'status': 'missing',
                    'error': 'Skill not found'
                }
                report['compatible'] = False
                report['errors'].append(f"Skill {skill_name} not found")
                continue

            skill_report = {
                'current_version': skill.current_version,
                'required_version': skill_req.get('version'),
                'min_version': skill_req.get('min_version'),
                'max_version': skill_req.get('max_version'),
                'status': 'compatible',
                'warnings': [],
                'errors': []
            }

            # Check version compatibility
            min_version = skill_req.get('min_version')
            if min_version and skill._compare_versions(skill.current_version, min_version) < 0:
                skill_report['status'] = 'incompatible'
                skill_report['errors'].append(f"Current version too old (requires >={min_version})")
                report['compatible'] = False

            max_version = skill_req.get('max_version')
            if max_version and skill._compare_versions(skill.current_version, max_version) > 0:
                skill_report['warnings'].append(f"Current version newer than required (requires <={max_version})")

            # Check for updates available
            if skill.available_versions:
                latest = max(skill.available_versions, key=skill._parse_version)
                if skill._compare_versions(latest, skill.current_version) > 0:
                    skill_report['update_available'] = latest
                    report['warnings'].append(f"Update available for {skill_name}: {skill.current_version} → {latest}")

            report['skills'][skill_name] = skill_report

        return report
