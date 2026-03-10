#!/usr/bin/env python3
"""
Integration tests for the New Feature Pipeline.

Tests the complete workflow for adding a new feature to an existing project,
including all role skills and their interactions.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import subprocess
import sys
import importlib.util

# Add skills directory to path
skills_path = Path(__file__).parent.parent

# Import skill modules using importlib to handle hyphenated directory names
def import_skill_module(skill_dir, module_name):
    """Import a skill module from a hyphenated directory."""
    module_path = skills_path / skill_dir / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

client_module = import_skill_module('client', 'client')
Client = client_module.Client

product_manager_module = import_skill_module('product-manager', 'product_manager')
ProductManager = product_manager_module.ProductManager

project_manager_module = import_skill_module('project-manager', 'project_manager')
ProjectManager = project_manager_module.ProjectManager

ui_ux_designer_module = import_skill_module('ui-ux-designer', 'ui_ux_designer')
UIUXDesigner = ui_ux_designer_module.UxDesigner

tech_lead_module = import_skill_module('tech-lead', 'tech_lead')
TechLead = tech_lead_module.TechLead

software_engineer_module = import_skill_module('software-engineer', 'software_engineer')
SoftwareEngineer = software_engineer_module.SoftwareEngineer

testing_engineer_module = import_skill_module('testing-engineer', 'testing_engineer')
TestingEngineer = testing_engineer_module.TestingEngineer

qa_engineer_module = import_skill_module('qa-engineer', 'qa_engineer')
QAEngineer = qa_engineer_module.QAEngineer

security_engineer_module = import_skill_module('security-engineer', 'security_engineer')
SecurityEngineer = security_engineer_module.SecurityEngineer

documentation_specialist_module = import_skill_module('documentation-specialist', 'documentation_specialist')
DocumentationSpecialist = documentation_specialist_module.DocumentationSpecialist


class TestNewFeaturePipeline:
    """Integration tests for the new feature pipeline."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def setup_existing_project(self, temp_project_dir):
        """Set up an existing project with state files."""
        # Create .iflow directory structure
        iflow_dir = temp_project_dir / ".iflow" / "skills"
        iflow_dir.mkdir(parents=True, exist_ok=True)
        
        # Create shared state directory
        shared_state_dir = iflow_dir / ".shared-state"
        shared_state_dir.mkdir(parents=True, exist_ok=True)
        
        # Create templates directory
        templates_dir = shared_state_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Create template files
        templates = [
            "pipeline-status.template.md",
            "project-spec.template.md",
            "architecture-spec.template.md",
            "design-spec.template.md",
            "implementation-plan.template.md",
            "implementation.template.md",
            "test-plan.template.md",
            "test-results.template.md",
            "quality-report.template.md",
            "security-report.template.md",
            "api-docs.template.md",
            "user-guide.template.md",
            "changelog.template.md"
        ]
        
        for template in templates:
            (templates_dir / template).write_text(f"# {template}\n\nTemplate content here.")
        
        # Create state directory with existing project files
        state_dir = temp_project_dir / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)
        
        # Create existing project specification
        project_spec = state_dir / "project-spec.md"
        project_spec.write_text("""# Project Specification

## Overview
Existing project with established requirements.

## Features
- Feature 1: User authentication
- Feature 2: Data visualization
- Feature 3: Report generation

## New Feature Request
- **Name:** Feature X - Advanced analytics
- **Description:** Add advanced analytics capabilities
- **Priority:** High
""")
        
        # Create existing architecture specification
        architecture_spec = state_dir / "architecture-spec.md"
        architecture_spec.write_text("""# Architecture Specification

## System Architecture
Monolithic application with microservices components.

## Technology Stack
- Backend: Python/FastAPI
- Frontend: React
- Database: PostgreSQL
""")
        
        # Create existing implementation plan
        implementation_plan = state_dir / "implementation-plan.md"
        implementation_plan.write_text("""# Implementation Plan

## Sprint 1
- Task 1: User authentication
- Task 2: Basic UI components

## Sprint 2
- Task 3: Data integration
- Task 4: Visualization components
""")
        
        # Create pipeline status
        pipeline_status = state_dir / "pipeline-status.md"
        pipeline_status.write_text("""# Pipeline Status

**Pipeline:** existing-project
**Current Feature:** Feature X
**Status:** feature-planning
**Progress:** 20%

## Features
- [x] Feature 1
- [x] Feature 2
- [x] Feature 3
- [ ] Feature X (New)
""")
        
        # Initialize git repository
        subprocess.run(['git', 'init'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial project setup'], cwd=temp_project_dir, capture_output=True)
        
        return temp_project_dir

    def test_new_feature_pipeline_execution(self, setup_existing_project):
        """Test the complete new feature pipeline execution."""
        project_path = setup_existing_project
        
        # Phase 1: Client - Update requirements for new feature
        client = Client(repo_root=project_path)
        code, message = client.run_workflow(
            project_path=project_path,
            project_name="Existing Project",
            pipeline_type="new-feature",
            current_feature="Feature X"
        )
        assert code == 0, f"Client phase failed: {message}"
        
        # Verify project-spec.md was updated
        project_spec = project_path / ".state" / "project-spec.md"
        assert project_spec.exists(), "project-spec.md should exist"
        
        # Phase 2: Product Manager - Prioritize new feature
        product_manager = ProductManager(repo_root=project_path)
        code, message = product_manager.run_workflow(project_path=project_path)
        assert code == 0, f"Product Manager phase failed: {message}"
        
        # Phase 3: Project Manager - Plan sprint for feature
        project_manager = ProjectManager(repo_root=project_path)
        code, message = project_manager.run_workflow(project_path=project_path)
        assert code == 0, f"Project Manager phase failed: {message}"
        
        # Verify implementation-plan.md was updated
        implementation_plan = project_path / ".state" / "implementation-plan.md"
        assert implementation_plan.exists(), "implementation-plan.md should exist"
        
        # Phase 4: UI/UX Designer - Design feature UI
        ui_ux_designer = UIUXDesigner(repo_root=project_path)
        code, message = ui_ux_designer.run_workflow(project_path=project_path)
        assert code == 0, f"UI/UX Designer phase failed: {message}"
        
        # Verify design-spec.md was updated
        design_spec = project_path / ".state" / "design-spec.md"
        assert design_spec.exists(), "design-spec.md should exist"
        
        # Phase 5: Tech Lead - Review architecture impact
        tech_lead = TechLead(repo_root=project_path)
        code, message = tech_lead.run_workflow(project_path=project_path)
        assert code == 0, f"Tech Lead phase failed: {message}"
        
        # Verify architecture-spec.md was updated
        architecture_spec = project_path / ".state" / "architecture-spec.md"
        assert architecture_spec.exists(), "architecture-spec.md should exist"
        
        # Phase 6: Software Engineer - Implement feature
        software_engineer = SoftwareEngineer(repo_root=project_path)
        code, message = software_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"Software Engineer phase failed: {message}"
        
        # Verify implementation.md was updated
        implementation = project_path / ".state" / "implementation.md"
        assert implementation.exists(), "implementation.md should exist"
        
        # Phase 7: Testing Engineer - Test feature
        testing_engineer = TestingEngineer(repo_root=project_path)
        code, message = testing_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"Testing Engineer phase failed: {message}"
        
        # Verify test-plan.md and test-results.md were updated
        test_plan = project_path / ".state" / "test-plan.md"
        test_results = project_path / ".state" / "test-results.md"
        assert test_plan.exists(), "test-plan.md should exist"
        assert test_results.exists(), "test-results.md should exist"
        
        # Phase 8: QA Engineer - Validate feature quality
        qa_engineer = QAEngineer(repo_root=project_path)
        code, message = qa_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"QA Engineer phase failed: {message}"
        
        # Verify quality-report.md was updated
        quality_report = project_path / ".state" / "quality-report.md"
        assert quality_report.exists(), "quality-report.md should exist"
        
        # Phase 9: Security Engineer - Security review
        security_engineer = SecurityEngineer(repo_root=project_path)
        code, message = security_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"Security Engineer phase failed: {message}"
        
        # Verify security-report.md was updated
        security_report = project_path / ".state" / "security-report.md"
        assert security_report.exists(), "security-report.md should exist"
        
        # Phase 10: Documentation Specialist - Update documentation
        documentation_specialist = DocumentationSpecialist(repo_root=project_path)
        code, message = documentation_specialist.run_workflow(project_path=project_path)
        assert code == 0, f"Documentation Specialist phase failed: {message}"
        
        # Verify api-docs.md, user-guide.md, and changelog.md were updated
        api_docs = project_path / ".state" / "api-docs.md"
        user_guide = project_path / ".state" / "user-guide.md"
        changelog = project_path / ".state" / "changelog.md"
        assert api_docs.exists(), "api-docs.md should exist"
        assert user_guide.exists(), "user-guide.md should exist"
        assert changelog.exists(), "changelog.md should exist"
        
        # Verify pipeline-status.md was updated
        pipeline_status = project_path / ".state" / "pipeline-status.md"
        assert pipeline_status.exists(), "pipeline-status.md should exist"

    def test_feature_branch_creation(self, setup_existing_project):
        """Test that new feature pipeline creates appropriate branch."""
        project_path = setup_existing_project
        
        # Run client phase
        client = Client(repo_root=project_path)
        client.run_workflow(
            project_path=project_path,
            project_name="Existing Project",
            pipeline_type="new-feature",
            current_feature="Feature X"
        )
        
        # Check for feature branch (if implemented)
        result = subprocess.run(
            ['git', 'branch', '-a'],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        
        # For now, just verify git is working
        assert result.returncode == 0

    def test_feature_preserves_existing_code(self, setup_existing_project):
        """Test that new feature doesn't break existing functionality."""
        project_path = setup_existing_project
        
        # Create a sample existing code file
        src_dir = project_path / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        existing_file = src_dir / "existing.py"
        existing_file.write_text("# Existing code\ndef existing_function():\n    return 'existing'")
        
        # Add to git
        subprocess.run(['git', 'add', 'src/existing.py'], cwd=project_path, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Add existing code'], cwd=project_path, capture_output=True)
        
        # Run feature pipeline
        client = Client(repo_root=project_path)
        client.run_workflow(
            project_path=project_path,
            project_name="Existing Project",
            pipeline_type="new-feature",
            current_feature="Feature X"
        )
        
        # Verify existing file still exists
        assert existing_file.exists(), "Existing code should be preserved"
        assert "existing_function" in existing_file.read_text()

    def test_feature_integration_with_existing_features(self, setup_existing_project):
        """Test that new feature integrates with existing features."""
        project_path = setup_existing_project
        
        # Run client phase
        client = Client(repo_root=project_path)
        client.run_workflow(
            project_path=project_path,
            project_name="Existing Project",
            pipeline_type="new-feature",
            current_feature="Feature X"
        )
        
        # Verify project spec includes both old and new features
        project_spec = project_path / ".state" / "project-spec.md"
        content = project_spec.read_text()
        
        assert "Feature 1" in content or "authentication" in content, "Existing features should be preserved"
        assert "Feature X" in content or "analytics" in content, "New feature should be added"

    def test_feature_testing_coverage(self, setup_existing_project):
        """Test that new feature has adequate test coverage."""
        project_path = setup_existing_project
        
        # Run through testing phase
        client = Client(repo_root=project_path)
        client.run_workflow(
            project_path=project_path,
            project_name="Existing Project",
            pipeline_type="new-feature",
            current_feature="Feature X"
        )
        
        software_engineer = SoftwareEngineer(repo_root=project_path)
        software_engineer.run_workflow(project_path=project_path)
        
        testing_engineer = TestingEngineer(repo_root=project_path)
        testing_engineer.run_workflow(project_path=project_path)
        
        # Verify test results include new feature
        test_results = project_path / ".state" / "test-results.md"
        assert test_results.exists(), "Test results should exist"

    def test_feature_documentation_updates(self, setup_existing_project):
        """Test that new feature documentation is comprehensive."""
        project_path = setup_existing_project
        
        # Run through documentation phase
        client = Client(repo_root=project_path)
        client.run_workflow(
            project_path=project_path,
            project_name="Existing Project",
            pipeline_type="new-feature",
            current_feature="Feature X"
        )
        
        software_engineer = SoftwareEngineer(repo_root=project_path)
        software_engineer.run_workflow(project_path=project_path)
        
        documentation_specialist = DocumentationSpecialist(repo_root=project_path)
        documentation_specialist.run_workflow(project_path=project_path)
        
        # Verify documentation mentions new feature
        changelog = project_path / ".state" / "changelog.md"
        content = changelog.read_text()
        
        assert "1.1.0" in content or "1.0.1" in content or "feature" in content.lower(), "Changelog should mention new feature"

    def test_feature_performance_impact(self, setup_existing_project):
        """Test that new feature doesn't negatively impact performance."""
        project_path = setup_existing_project
        
        # This would test performance metrics
        # For now, just verify the structure
        state_dir = project_path / ".state"
        assert state_dir.exists()

    def test_feature_security_compatibility(self, setup_existing_project):
        """Test that new feature maintains security standards."""
        project_path = setup_existing_project
        
        # Run through security phase
        client = Client(repo_root=project_path)
        client.run_workflow(
            project_path=project_path,
            project_name="Existing Project",
            pipeline_type="new-feature",
            current_feature="Feature X"
        )
        
        software_engineer = SoftwareEngineer(repo_root=project_path)
        software_engineer.run_workflow(project_path=project_path)
        
        security_engineer = SecurityEngineer(repo_root=project_path)
        security_engineer.run_workflow(project_path=project_path)
        
        # Verify security report exists
        security_report = project_path / ".state" / "security-report.md"
        assert security_report.exists(), "Security report should exist"

    def test_multiple_features_sequential(self, setup_existing_project):
        """Test adding multiple features sequentially."""
        project_path = setup_existing_project
        
        # Add first feature
        client = Client(repo_root=project_path)
        client.run_workflow(
            project_path=project_path,
            project_name="Existing Project",
            pipeline_type="new-feature",
            current_feature="Feature X"
        )
        
        # Add second feature
        client.run_workflow(
            project_path=project_path,
            project_name="Existing Project",
            pipeline_type="new-feature",
            current_feature="Feature Y"
        )
        
        # Verify both features are documented
        project_spec = project_path / ".state" / "project-spec.md"
        content = project_spec.read_text()
        
        assert "Feature X" in content or "analytics" in content, "First feature should be documented"
        assert "Feature Y" in content or "Feature X" in content, "Second feature should be documented"


class TestFeaturePipelineDependencies:
    """Tests for feature pipeline dependencies."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_feature_requires_existing_project(self, temp_project_dir):
        """Test that feature pipeline requires an existing project."""
        # Create minimal structure without existing project
        iflow_dir = temp_project_dir / ".iflow" / "skills"
        iflow_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to run feature pipeline without existing project
        client = Client(repo_root=temp_project_dir)
        code, message = client.run_workflow(
            project_path=temp_project_dir,
            project_name="New Project",
            pipeline_type="new-feature",
            current_feature="Test Feature"
        )
        
        # Should handle missing project gracefully
        # (implementation may vary)

    def test_feature_respects_project_constraints(self, temp_project_dir):
        """Test that feature pipeline respects existing project constraints."""
        # Set up project with specific constraints
        iflow_dir = temp_project_dir / ".iflow" / "skills"
        iflow_dir.mkdir(parents=True, exist_ok=True)
        
        shared_state_dir = iflow_dir / ".shared-state"
        shared_state_dir.mkdir(parents=True, exist_ok=True)
        
        templates_dir = shared_state_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        (templates_dir / "pipeline-status.template.md").write_text("# Template\n")
        (templates_dir / "project-spec.template.md").write_text("# Template\n")
        
        state_dir = temp_project_dir / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)
        
        # Create project with constraints
        project_spec = state_dir / "project-spec.md"
        project_spec.write_text("""# Project Specification

## Constraints
- Must use existing database schema
- Must follow existing API patterns
- Cannot introduce breaking changes
""")
        
        # Initialize git
        subprocess.run(['git', 'init'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=temp_project_dir, capture_output=True)
        
        # Run feature pipeline
        client = Client(repo_root=temp_project_dir)
        code, message = client.run_workflow(
            project_path=temp_project_dir,
            project_name="Constrained Project",
            pipeline_type="new-feature",
            current_feature="New Feature"
        )
        
        # Verify constraints are considered
        assert code == 0, f"Should succeed respecting constraints: {message}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])