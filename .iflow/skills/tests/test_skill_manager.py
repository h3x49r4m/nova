#!/usr/bin/env python3
"""
Test suite for skill_manager.py
Tests version management, capabilities, compatibility checking, and dependency resolution.
"""

import json
import tempfile
import unittest
from pathlib import Path

from skill_manager import (
    SkillVersionManager,
    SkillRegistry,
    SkillDependencyResolver,
    SkillCompatibilityChecker
)


class TestSkillVersionManager(unittest.TestCase):
    """Test SkillVersionManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.skills_dir = Path(self.temp_dir)
        self.skill_name = "test-skill"
        self.skill_dir = self.skills_dir / self.skill_name
        self.versions_dir = self.skill_dir / 'versions'
        self.config_file = self.skill_dir / 'config.json'

        # Create skill directory structure
        self.versions_dir.mkdir(parents=True)
        self.config_file.touch()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_load_current_version_default(self):
        """Test loading current version defaults to 1.0.0."""
        manager = SkillVersionManager(self.skill_name, self.skills_dir)
        self.assertEqual(manager.current_version, "1.0.0")

    def test_load_current_version_from_config(self):
        """Test loading current version from config file."""
        config = {"version": "2.1.3"}
        self.config_file.write_text(json.dumps(config))
        
        manager = SkillVersionManager(self.skill_name, self.skills_dir)
        self.assertEqual(manager.current_version, "2.1.3")

    def test_parse_version(self):
        """Test semantic version parsing."""
        manager = SkillVersionManager(self.skill_name, self.skills_dir)
        
        self.assertEqual(manager._parse_version("1.0.0"), (1, 0, 0))
        self.assertEqual(manager._parse_version("2.3.4"), (2, 3, 4))
        self.assertEqual(manager._parse_version("10.20.30"), (10, 20, 30))

    def test_compare_versions(self):
        """Test version comparison."""
        manager = SkillVersionManager(self.skill_name, self.skills_dir)
        
        self.assertEqual(manager._compare_versions("1.0.0", "2.0.0"), -1)
        self.assertEqual(manager._compare_versions("2.0.0", "1.0.0"), 1)
        self.assertEqual(manager._compare_versions("1.0.0", "1.0.0"), 0)
        self.assertEqual(manager._compare_versions("1.2.3", "1.2.4"), -1)
        self.assertEqual(manager._compare_versions("1.2.4", "1.2.3"), 1)

    def test_check_version_compatibility(self):
        """Test version compatibility checking."""
        manager = SkillVersionManager(self.skill_name, self.skills_dir)
        manager.current_version = "2.5.0"
        
        self.assertTrue(manager.check_version_compatibility("2.0.0", ">="))
        self.assertTrue(manager.check_version_compatibility("2.5.0", "=="))
        self.assertFalse(manager.check_version_compatibility("3.0.0", "<="))
        self.assertTrue(manager.check_version_compatibility("2.0.0", ">"))
        self.assertFalse(manager.check_version_compatibility("2.5.0", ">"))
        self.assertTrue(manager.check_version_compatibility("3.0.0", "<"))

    def test_load_available_versions(self):
        """Test loading available versions."""
        # Create version directories
        (self.versions_dir / "1.0.0").mkdir()
        (self.versions_dir / "2.0.0").mkdir()
        (self.versions_dir / "1.5.0").mkdir()
        
        manager = SkillVersionManager(self.skill_name, self.skills_dir)
        versions = manager.available_versions
        
        self.assertEqual(versions, ["1.0.0", "1.5.0", "2.0.0"])

    def test_find_compatible_version(self):
        """Test finding compatible version within range."""
        # Create version directories
        (self.versions_dir / "1.0.0").mkdir()
        (self.versions_dir / "1.5.0").mkdir()
        (self.versions_dir / "2.0.0").mkdir()
        (self.versions_dir / "2.5.0").mkdir()
        
        manager = SkillVersionManager(self.skill_name, self.skills_dir)
        
        # Test min version
        result = manager.find_compatible_version(min_version="1.5.0")
        self.assertEqual(result, "2.5.0")
        
        # Test max version
        result = manager.find_compatible_version(max_version="1.5.0")
        self.assertEqual(result, "1.5.0")
        
        # Test range
        result = manager.find_compatible_version(min_version="1.2.0", max_version="2.0.0")
        self.assertEqual(result, "2.0.0")

    def test_load_capabilities(self):
        """Test loading capabilities from version directories."""
        # Create version with capabilities
        version_dir = self.versions_dir / "1.0.0"
        version_dir.mkdir()
        
        capabilities_file = version_dir / 'capabilities.json'
        capabilities = {
            "capabilities": ["test-capability"],
            "domains": {"test": {"supported": True}}
        }
        capabilities_file.write_text(json.dumps(capabilities))
        
        manager = SkillVersionManager(self.skill_name, self.skills_dir)
        caps = manager.get_capabilities("1.0.0")
        
        self.assertEqual(caps["capabilities"], ["test-capability"])
        self.assertTrue(caps["domains"]["test"]["supported"])


class TestSkillRegistry(unittest.TestCase):
    """Test SkillRegistry class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.skills_dir = Path(self.temp_dir)
        
        # Create multiple skills
        self._create_skill("skill-a", "1.0.0")
        self._create_skill("skill-b", "2.1.0")
        self._create_skill("skill-c", "1.5.0")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def _create_skill(self, name, version):
        """Helper to create a skill with version."""
        skill_dir = self.skills_dir / name
        skill_dir.mkdir()
        
        # Create config
        config_file = skill_dir / 'config.json'
        config = {"version": version}
        config_file.write_text(json.dumps(config))
        
        # Create SKILL.md
        skill_file = skill_dir / 'SKILL.md'
        skill_file.write_text(f"# {name}")
        
        # Create version directory
        versions_dir = skill_dir / 'versions' / version
        versions_dir.mkdir(parents=True)
        
        capabilities_file = versions_dir / 'capabilities.json'
        capabilities = {
            "capabilities": [f"{name}-capability"],
            "domains": {}
        }
        capabilities_file.write_text(json.dumps(capabilities))

    def test_load_all_skills(self):
        """Test loading all skills."""
        registry = SkillRegistry(self.skills_dir)
        
        self.assertEqual(len(registry.skills), 3)
        self.assertIn("skill-a", registry.skills)
        self.assertIn("skill-b", registry.skills)
        self.assertIn("skill-c", registry.skills)

    def test_get_skill(self):
        """Test getting a skill by name."""
        registry = SkillRegistry(self.skills_dir)
        
        skill = registry.get_skill("skill-a")
        self.assertIsNotNone(skill)
        self.assertEqual(skill.skill_name, "skill-a")
        
        skill = registry.get_skill("nonexistent")
        self.assertIsNone(skill)

    def test_list_skills(self):
        """Test listing all skills."""
        registry = SkillRegistry(self.skills_dir)
        skills = registry.list_skills()
        
        self.assertEqual(sorted(skills), ["skill-a", "skill-b", "skill-c"])

    def test_get_skill_capabilities(self):
        """Test getting capabilities for a specific skill version."""
        registry = SkillRegistry(self.skills_dir)
        
        caps = registry.get_skill_capabilities("skill-a", "1.0.0")
        self.assertEqual(caps["capabilities"], ["skill-a-capability"])

    def test_find_skill_for_capability(self):
        """Test finding skills by capability."""
        registry = SkillRegistry(self.skills_dir)
        
        # Add shared capability to skill-b
        skill_b_dir = self.skills_dir / "skill-b" / "versions" / "2.1.0"
        capabilities_file = skill_b_dir / 'capabilities.json'
        capabilities = {
            "capabilities": ["shared-capability", "skill-b-capability"],
            "domains": {}
        }
        capabilities_file.write_text(json.dumps(capabilities))
        
        results = registry.find_skill_for_capability("shared-capability")
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "skill-b")


class TestSkillDependencyResolver(unittest.TestCase):
    """Test SkillDependencyResolver class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.skills_dir = Path(self.temp_dir)
        
        # Create skills with dependencies
        self._create_skill("base-skill", "1.0.0", {})
        self._create_skill("dependent-skill", "1.0.0", {
            "base-skill": {"min_version": "1.0.0"}
        })
        
        self.registry = SkillRegistry(self.skills_dir)
        self.resolver = SkillDependencyResolver(self.registry)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def _create_skill(self, name, version, dependencies):
        """Helper to create a skill with dependencies."""
        skill_dir = self.skills_dir / name
        skill_dir.mkdir()
        
        config_file = skill_dir / 'config.json'
        config = {"version": version}
        config_file.write_text(json.dumps(config))
        
        skill_file = skill_dir / 'SKILL.md'
        skill_file.write_text(f"# {name}")
        
        versions_dir = skill_dir / 'versions' / version
        versions_dir.mkdir(parents=True)
        
        capabilities_file = versions_dir / 'capabilities.json'
        capabilities = {
            "capabilities": [f"{name}-capability"],
            "domains": {},
            "dependencies": dependencies
        }
        capabilities_file.write_text(json.dumps(capabilities))

    def test_resolve_pipeline_requirements_success(self):
        """Test resolving pipeline requirements successfully."""
        pipeline_config = {
            "skills": {
                "base-skill": {"min_version": "1.0.0"},
                "dependent-skill": {"min_version": "1.0.0"}
            }
        }
        
        success, versions, errors = self.resolver.resolve_pipeline_requirements(pipeline_config)
        
        self.assertTrue(success)
        self.assertEqual(versions["base-skill"], "1.0.0")
        self.assertEqual(versions["dependent-skill"], "1.0.0")
        self.assertEqual(len(errors), 0)

    def test_resolve_pipeline_requirements_missing_skill(self):
        """Test resolving requirements with missing skill."""
        pipeline_config = {
            "skills": {
                "nonexistent-skill": {"min_version": "1.0.0"}
            }
        }
        
        success, versions, errors = self.resolver.resolve_pipeline_requirements(pipeline_config)
        
        self.assertFalse(success)
        self.assertIn("Skill 'nonexistent-skill' not found", errors)

    def test_validate_workflow_state_compatibility(self):
        """Test validating workflow state compatibility."""
        workflow_state = {
            "skills_used": {
                "base-skill": "1.0.0",
                "dependent-skill": "1.0.0"
            }
        }
        
        is_valid, errors = self.resolver.validate_workflow_state_compatibility(workflow_state)
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_workflow_state_incompatible_version(self):
        """Test validating workflow with incompatible version."""
        workflow_state = {
            "skills_used": {
                "base-skill": "99.0.0"  # Non-existent version
            }
        }
        
        is_valid, errors = self.resolver.validate_workflow_state_compatibility(workflow_state)
        
        self.assertFalse(is_valid)
        self.assertTrue(any("no longer available" in e for e in errors))


class TestSkillCompatibilityChecker(unittest.TestCase):
    """Test SkillCompatibilityChecker class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.skills_dir = Path(self.temp_dir)
        
        # Create skills
        self._create_skill("test-skill", "2.0.0")
        
        self.registry = SkillRegistry(self.skills_dir)
        self.checker = SkillCompatibilityChecker(self.registry)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def _create_skill(self, name, version):
        """Helper to create a skill."""
        skill_dir = self.skills_dir / name
        skill_dir.mkdir()
        
        config_file = skill_dir / 'config.json'
        config = {"version": version}
        config_file.write_text(json.dumps(config))
        
        skill_file = skill_dir / 'SKILL.md'
        skill_file.write_text(f"# {name}")
        
        versions_dir = skill_dir / 'versions' / version
        versions_dir.mkdir(parents=True)
        
        capabilities_file = versions_dir / 'capabilities.json'
        capabilities = {
            "capabilities": [f"{name}-capability"],
            "domains": {},
            "compatible_pipelines": ["*"]
        }
        capabilities_file.write_text(json.dumps(capabilities))

    def test_check_pipeline_compatibility_success(self):
        """Test checking pipeline compatibility successfully."""
        pipeline_config = {
            "pipeline": "test-pipeline",
            "skills": {
                "test-skill": {"min_version": "1.0.0", "max_version": "3.0.0"}
            }
        }
        
        is_compatible, errors = self.checker.check_pipeline_compatibility("test-pipeline", pipeline_config)
        
        self.assertTrue(is_compatible)
        self.assertEqual(len(errors), 0)

    def test_check_pipeline_compatibility_version_mismatch(self):
        """Test checking pipeline with version mismatch."""
        pipeline_config = {
            "pipeline": "test-pipeline",
            "skills": {
                "test-skill": {"min_version": "3.0.0"}  # Current is 2.0.0
            }
        }
        
        is_compatible, errors = self.checker.check_pipeline_compatibility("test-pipeline", pipeline_config)
        
        self.assertFalse(is_compatible)
        self.assertTrue(any("too old" in e for e in errors))

    def test_check_skill_breaking_changes(self):
        """Test checking for breaking changes between versions."""
        # Create another version with breaking changes
        skill_dir = self.skills_dir / "test-skill"
        version_dir = skill_dir / 'versions' / '3.0.0'
        version_dir.mkdir(parents=True)
        
        capabilities_file = version_dir / 'capabilities.json'
        capabilities = {
            "capabilities": ["test-skill-capability"],
            "domains": {},
            "compatible_pipelines": ["*"]
        }
        capabilities_file.write_text(json.dumps(capabilities))
        
        breaking_file = version_dir / 'breaking_changes.json'
        breaking_changes = ["API change: endpoint /old removed"]
        breaking_file.write_text(json.dumps(breaking_changes))
        
        changes = self.checker.check_skill_breaking_changes("test-skill", "2.0.0", "3.0.0")
        
        self.assertEqual(len(changes), 1)
        self.assertIn("endpoint /old removed", changes[0])

    def test_generate_compatibility_report(self):
        """Test generating compatibility report."""
        pipeline_config = {
            "pipeline": "test-pipeline",
            "skills": {
                "test-skill": {"min_version": "1.0.0"}
            },
            "required_capabilities": ["test-skill-capability"]
        }
        
        report = self.checker.generate_compatibility_report(pipeline_config)
        
        self.assertTrue(report["compatible"])
        self.assertIn("test-skill", report["skills"])
        self.assertEqual(report["skills"]["test-skill"]["current_version"], "2.0.0")
        self.assertEqual(report["skills"]["test-skill"]["status"], "compatible")


if __name__ == '__main__':
    unittest.main()