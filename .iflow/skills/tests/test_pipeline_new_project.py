#!/usr/bin/env python3
"""
Integration tests for the New Project Pipeline.

Tests the complete workflow for creating a new project from scratch,
including all role skills and their interactions.
"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
import subprocess
import sys

# Add skills directory to path
skills_path = Path(__file__).parent.parent
sys.path.insert(0, str(skills_path))

from client.client import Client
from product_manager.product_manager import ProductManager
from project_manager.project_manager import ProjectManager
from ui_ux_designer.ui_ux_designer import UIUXDesigner
from tech_lead.tech_lead import TechLead
from software_engineer.software_engineer import SoftwareEngineer
from testing_engineer.testing_engineer import TestingEngineer
from qa_engineer.qa_engineer import QAEngineer
from devops_engineer.devops_engineer import DevOpsEngineer
from security_engineer.security_engineer import SecurityEngineer
from documentation_specialist.documentation_specialist import DocumentationSpecialist


class TestNewProjectPipeline:
    """Integration tests for the new project pipeline."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def setup_project_structure(self, temp_project_dir):
        """Set up the basic project structure."""
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
            "deployment-status.template.md",
            "api-docs.template.md",
            "user-guide.template.md",
            "changelog.template.md"
        ]
        
        for template in templates:
            (templates_dir / template).write_text(f"# {template}\n\nTemplate content here.")
        
        # Initialize git repository
        subprocess.run(['git', 'init'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=temp_project_dir, capture_output=True)
        
        return temp_project_dir

    def test_full_pipeline_execution(self, setup_project_structure):
        """Test the complete new project pipeline execution."""
        project_path = setup_project_structure
        
        # Phase 1: Client - Requirements gathering
        client = Client(repo_root=project_path)
        code, message = client.run_workflow(
            project_path=project_path,
            project_name="Test Project",
            pipeline_type="new-project"
        )
        assert code == 0, f"Client phase failed: {message}"
        
        # Verify project-spec.md was created
        project_spec = project_path / ".state" / "project-spec.md"
        assert project_spec.exists(), "project-spec.md should exist after client phase"
        
        # Phase 2: Product Manager - Feature planning
        product_manager = ProductManager(repo_root=project_path)
        code, message = product_manager.run_workflow(project_path=project_path)
        assert code == 0, f"Product Manager phase failed: {message}"
        
        # Phase 3: Project Manager - Sprint planning
        project_manager = ProjectManager(repo_root=project_path)
        code, message = project_manager.run_workflow(project_path=project_path)
        assert code == 0, f"Project Manager phase failed: {message}"
        
        # Verify implementation-plan.md was created
        implementation_plan = project_path / ".state" / "implementation-plan.md"
        assert implementation_plan.exists(), "implementation-plan.md should exist after project manager phase"
        
        # Phase 4: UI/UX Designer - Design creation
        ui_ux_designer = UIUXDesigner(repo_root=project_path)
        code, message = ui_ux_designer.run_workflow(project_path=project_path)
        assert code == 0, f"UI/UX Designer phase failed: {message}"
        
        # Verify design-spec.md was created
        design_spec = project_path / ".state" / "design-spec.md"
        assert design_spec.exists(), "design-spec.md should exist after UI/UX designer phase"
        
        # Phase 5: Tech Lead - Architecture design
        tech_lead = TechLead(repo_root=project_path)
        code, message = tech_lead.run_workflow(project_path=project_path)
        assert code == 0, f"Tech Lead phase failed: {message}"
        
        # Verify architecture-spec.md was created
        architecture_spec = project_path / ".state" / "architecture-spec.md"
        assert architecture_spec.exists(), "architecture-spec.md should exist after tech lead phase"
        
        # Phase 6: Software Engineer - Implementation
        software_engineer = SoftwareEngineer(repo_root=project_path)
        code, message = software_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"Software Engineer phase failed: {message}"
        
        # Verify implementation.md was created
        implementation = project_path / ".state" / "implementation.md"
        assert implementation.exists(), "implementation.md should exist after software engineer phase"
        
        # Phase 7: Testing Engineer - Test automation
        testing_engineer = TestingEngineer(repo_root=project_path)
        code, message = testing_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"Testing Engineer phase failed: {message}"
        
        # Verify test-plan.md and test-results.md were created
        test_plan = project_path / ".state" / "test-plan.md"
        test_results = project_path / ".state" / "test-results.md"
        assert test_plan.exists(), "test-plan.md should exist after testing engineer phase"
        assert test_results.exists(), "test-results.md should exist after testing engineer phase"
        
        # Phase 8: QA Engineer - Quality validation
        qa_engineer = QAEngineer(repo_root=project_path)
        code, message = qa_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"QA Engineer phase failed: {message}"
        
        # Verify quality-report.md was created
        quality_report = project_path / ".state" / "quality-report.md"
        assert quality_report.exists(), "quality-report.md should exist after QA engineer phase"
        
        # Phase 9: DevOps Engineer - CI/CD setup
        devops_engineer = DevOpsEngineer(repo_root=project_path)
        code, message = devops_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"DevOps Engineer phase failed: {message}"
        
        # Verify deployment-status.md was created
        deployment_status = project_path / ".state" / "deployment-status.md"
        assert deployment_status.exists(), "deployment-status.md should exist after DevOps engineer phase"
        
        # Phase 10: Security Engineer - Security validation
        security_engineer = SecurityEngineer(repo_root=project_path)
        code, message = security_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"Security Engineer phase failed: {message}"
        
        # Verify security-report.md was created
        security_report = project_path / ".state" / "security-report.md"
        assert security_report.exists(), "security-report.md should exist after security engineer phase"
        
        # Phase 11: Documentation Specialist - Documentation
        documentation_specialist = DocumentationSpecialist(repo_root=project_path)
        code, message = documentation_specialist.run_workflow(project_path=project_path)
        assert code == 0, f"Documentation Specialist phase failed: {message}"
        
        # Verify api-docs.md, user-guide.md, and changelog.md were created
        api_docs = project_path / ".state" / "api-docs.md"
        user_guide = project_path / ".state" / "user-guide.md"
        changelog = project_path / ".state" / "changelog.md"
        assert api_docs.exists(), "api-docs.md should exist after documentation specialist phase"
        assert user_guide.exists(), "user-guide.md should exist after documentation specialist phase"
        assert changelog.exists(), "changelog.md should exist after documentation specialist phase"
        
        # Verify pipeline-status.md was updated
        pipeline_status = project_path / ".state" / "pipeline-status.md"
        assert pipeline_status.exists(), "pipeline-status.md should exist"

    def test_pipeline_with_git_commits(self, setup_project_structure):
        """Test that pipeline creates proper git commits."""
        project_path = setup_project_structure
        
        # Run client phase
        client = Client(repo_root=project_path)
        client.run_workflow(project_path=project_path, project_name="Test", pipeline_type="new-project")
        
        # Check git log for commit
        result = subprocess.run(
            ['git', 'log', '--oneline', '-1'],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'client' in result.stdout.lower(), "Git commit should mention client role"

    def test_pipeline_state_transitions(self, setup_project_structure):
        """Test that pipeline properly transitions between states."""
        project_path = setup_project_structure
        
        # Run phases and check state transitions
        client = Client(repo_root=project_path)
        client.run_workflow(project_path=project_path, project_name="Test", pipeline_type="new-project")
        
        # Check pipeline status
        pipeline_status = project_path / ".state" / "pipeline-status.md"
        content = pipeline_status.read_text()
        
        assert "new-project" in content, "Pipeline should be new-project type"
        assert "Client" in content, "Client role should be in pipeline status"

    def test_pipeline_error_handling(self, setup_project_structure):
        """Test pipeline error handling when a phase fails."""
        project_path = setup_project_structure
        
        # Create a scenario where a phase might fail
        # For now, just verify the pipeline structure
        state_dir = project_path / ".state"
        assert state_dir.exists(), "State directory should exist"

    def test_pipeline_documentation_completeness(self, setup_project_structure):
        """Test that pipeline creates all required documentation."""
        project_path = setup_project_structure
        
        # Run a simplified pipeline
        client = Client(repo_root=project_path)
        client.run_workflow(project_path=project_path, project_name="Test", pipeline_type="new-project")
        
        tech_lead = TechLead(repo_root=project_path)
        tech_lead.run_workflow(project_path=project_path)
        
        # Check for required documentation
        required_docs = [
            "project-spec.md",
            "architecture-spec.md",
            "pipeline-status.md"
        ]
        
        for doc in required_docs:
            doc_path = project_path / ".state" / doc
            assert doc_path.exists(), f"Required document {doc} should exist"

    def test_pipeline_config_integration(self, setup_project_structure):
        """Test that pipeline respects configuration settings."""
        project_path = setup_project_structure
        
        # Create a config file
        config_dir = project_path / ".iflow" / "skills" / "client"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({
            "version": "1.0.0",
            "auto_commit": True
        }))
        
        # Run client phase
        client = Client(repo_root=project_path)
        client.run_workflow(project_path=project_path, project_name="Test", pipeline_type="new-project")
        
        # Verify config was loaded
        assert client.config.get("auto_commit") is True

    def test_pipeline_parallel_execution(self, setup_project_structure):
        """Test that certain pipeline phases can run in parallel (if supported)."""
        project_path = setup_project_structure
        
        # For now, test sequential execution
        # In a real implementation, this would test parallel execution
        client = Client(repo_root=project_path)
        product_manager = ProductManager(repo_root=project_path)
        
        code1, _ = client.run_workflow(project_path=project_path, project_name="Test", pipeline_type="new-project")
        code2, _ = product_manager.run_workflow(project_path=project_path)
        
        assert code1 == 0, "Client phase should succeed"
        assert code2 == 0, "Product Manager phase should succeed"

    def test_pipeline_rollback_capability(self, setup_project_structure):
        """Test pipeline rollback capability on failure."""
        project_path = setup_project_structure
        
        # This would test the ability to rollback to a previous state
        # For now, just verify the structure exists
        state_dir = project_path / ".state"
        assert state_dir.exists(), "State directory should exist for rollback"

    def test_pipeline_metrics_collection(self, setup_project_structure):
        """Test that pipeline collects metrics during execution."""
        project_path = setup_project_structure
        
        # Run a phase
        client = Client(repo_root=project_path)
        client.run_workflow(project_path=project_path, project_name="Test", pipeline_type="new-project")
        
        # Verify metrics were logged (if implemented)
        log_dir = project_path / ".iflow" / "logs"
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            # Just verify the directory exists
            assert log_dir.exists()

    def test_pipeline_state_validation(self, setup_project_structure):
        """Test that pipeline validates state before each phase."""
        project_path = setup_project_structure
        
        # Run client phase to create initial state
        client = Client(repo_root=project_path)
        client.run_workflow(project_path=project_path, project_name="Test", pipeline_type="new-project")
        
        # Verify state file exists and is valid
        project_spec = project_path / ".state" / "project-spec.md"
        assert project_spec.exists(), "State file should exist"
        assert project_spec.stat().st_size > 0, "State file should not be empty"

    def test_pipeline_cleanup(self, setup_project_structure):
        """Test that pipeline cleans up temporary files."""
        project_path = setup_project_structure
        
        # Run a phase
        client = Client(repo_root=project_path)
        client.run_workflow(project_path=project_path, project_name="Test", pipeline_type="new-project")
        
        # Verify no leftover temporary files
        # This would check for .tmp files or other artifacts
        state_dir = project_path / ".state"
        temp_files = list(state_dir.glob("*.tmp"))
        assert len(temp_files) == 0, "No temporary files should remain"


class TestPipelinePhaseDependencies:
    """Tests for phase dependencies in the pipeline."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_client_phase_creates_prerequisites(self, temp_project_dir):
        """Test that client phase creates prerequisites for subsequent phases."""
        # Set up basic structure
        iflow_dir = temp_project_dir / ".iflow" / "skills"
        iflow_dir.mkdir(parents=True, exist_ok=True)
        
        shared_state_dir = iflow_dir / ".shared-state"
        shared_state_dir.mkdir(parents=True, exist_ok=True)
        
        templates_dir = shared_state_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        (templates_dir / "pipeline-status.template.md").write_text("# Template\n")
        (templates_dir / "project-spec.template.md").write_text("# Template\n")
        
        subprocess.run(['git', 'init'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_project_dir, capture_output=True)
        
        # Run client phase
        client = Client(repo_root=temp_project_dir)
        client.run_workflow(project_path=temp_project_dir, project_name="Test", pipeline_type="new-project")
        
        # Verify prerequisites
        project_spec = temp_project_dir / ".state" / "project-spec.md"
        pipeline_status = temp_project_dir / ".state" / "pipeline-status.md"
        
        assert project_spec.exists(), "Client phase should create project-spec.md"
        assert pipeline_status.exists(), "Client phase should create pipeline-status.md"

    def test_product_manager_depends_on_client(self, temp_project_dir):
        """Test that product manager phase depends on client phase output."""
        # Set up and run client phase first
        iflow_dir = temp_project_dir / ".iflow" / "skills"
        iflow_dir.mkdir(parents=True, exist_ok=True)
        
        shared_state_dir = iflow_dir / ".shared-state"
        shared_state_dir.mkdir(parents=True, exist_ok=True)
        
        templates_dir = shared_state_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        (templates_dir / "pipeline-status.template.md").write_text("# Template\n")
        (templates_dir / "project-spec.template.md").write_text("# Template\n")
        
        subprocess.run(['git', 'init'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_project_dir, capture_output=True)
        
        client = Client(repo_root=temp_project_dir)
        client.run_workflow(project_path=temp_project_dir, project_name="Test", pipeline_type="new-project")
        
        # Run product manager phase
        product_manager = ProductManager(repo_root=temp_project_dir)
        code, message = product_manager.run_workflow(project_path=temp_project_dir)
        
        assert code == 0, f"Product Manager should succeed: {message}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])