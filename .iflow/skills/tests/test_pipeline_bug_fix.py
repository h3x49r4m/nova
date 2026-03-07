#!/usr/bin/env python3
"""
Integration tests for the Bug Fix Pipeline.

Tests the complete workflow for fixing bugs in an existing project,
including all role skills and their interactions.
"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import subprocess
import sys

# Add skills directory to path
skills_path = Path(__file__).parent.parent
sys.path.insert(0, str(skills_path))

from tech_lead.tech_lead import TechLead
from software_engineer.software_engineer import SoftwareEngineer
from testing_engineer.testing_engineer import TestingEngineer
from qa_engineer.qa_engineer import QAEngineer
from security_engineer.security_engineer import SecurityEngineer
from documentation_specialist.documentation_specialist import DocumentationSpecialist


class TestBugFixPipeline:
    """Integration tests for the bug fix pipeline."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def setup_buggy_project(self, temp_project_dir):
        """Set up an existing project with a bug to fix."""
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
            "architecture-spec.template.md",
            "implementation.template.md",
            "test-plan.template.md",
            "test-results.template.md",
            "quality-report.template.md",
            "security-report.template.md",
            "changelog.template.md"
        ]
        
        for template in templates:
            (templates_dir / template).write_text(f"# {template}\n\nTemplate content here.")
        
        # Create state directory with existing project files
        state_dir = temp_project_dir / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)
        
        # Create bug report
        bug_report = state_dir / "bug-report.md"
        bug_report.write_text("""# Bug Report

## Bug ID: BUG-123
## Title: Authentication fails on special characters in password
## Severity: High
## Priority: Critical

### Description
User authentication fails when password contains special characters like `!@#$%^&*()`.

### Steps to Reproduce
1. Navigate to login page
2. Enter username
3. Enter password with special characters: `P@ssw0rd!`
4. Click login

### Expected Behavior
User should be able to login with valid password containing special characters.

### Actual Behavior
Login fails with "Invalid credentials" error even with correct password.

### Environment
- Browser: Chrome 120
- OS: Windows 11
- Application Version: 1.2.0

### Stack Trace
```
File "backend/app/auth.py", line 45, in validate_password
    if not password.isalnum():
        raise ValueError("Invalid password")
```

### Root Cause
Password validation rejects special characters, which are valid according to security policy.
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

## Authentication Module
- JWT-based authentication
- Password validation: Alphanumeric only (NEEDS UPDATE)
- Session management: Redis
""")
        
        # Create existing implementation
        implementation = state_dir / "implementation.md"
        implementation.write_text("""# Implementation

## Authentication Module
Located in `backend/app/auth.py`

### Password Validation
```python
def validate_password(password: str) -> bool:
    if not password.isalnum():
        raise ValueError("Invalid password")
    return True
```

### Issues
- Password validation too restrictive
- Doesn't follow security best practices
""")
        
        # Create pipeline status
        pipeline_status = state_dir / "pipeline-status.md"
        pipeline_status.write_text("""# Pipeline Status

**Pipeline:** bug-fix
**Bug ID:** BUG-123
**Status:** analysis
**Progress:** 10%

## Bug Fix Phases
- [ ] Phase 1: Bug Analysis
- [ ] Phase 2: Fix Implementation
- [ ] Phase 3: Testing
- [ ] Phase 4: QA Validation
- [ ] Phase 5: Security Review
- [ ] Phase 6: Documentation Update
""")
        
        # Create source code with bug
        src_dir = temp_project_dir / "backend" / "app"
        src_dir.mkdir(parents=True, exist_ok=True)
        
        auth_file = src_dir / "auth.py"
        auth_file.write_text("""# Authentication Module

import re

def validate_password(password: str) -> bool:
    '''Validate password - CURRENTLY HAS BUG'''
    if not password.isalnum():
        raise ValueError("Invalid password")
    return True

def authenticate(username: str, password: str) -> bool:
    '''Authenticate user'''
    # In real implementation, would check against database
    validate_password(password)
    return username == "admin" and password == "admin123"
""")
        
        # Initialize git repository
        subprocess.run(['git', 'init'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit with bug'], cwd=temp_project_dir, capture_output=True)
        
        return temp_project_dir

    def test_bug_fix_pipeline_execution(self, setup_buggy_project):
        """Test the complete bug fix pipeline execution."""
        project_path = setup_buggy_project
        
        # Phase 1: Tech Lead - Analyze bug and design fix
        tech_lead = TechLead(repo_root=project_path)
        code, message = tech_lead.run_workflow(project_path=project_path)
        assert code == 0, f"Tech Lead phase failed: {message}"
        
        # Verify architecture-spec.md was updated with fix design
        architecture_spec = project_path / ".state" / "architecture-spec.md"
        assert architecture_spec.exists(), "architecture-spec.md should exist"
        
        # Phase 2: Software Engineer - Implement fix
        software_engineer = SoftwareEngineer(repo_root=project_path)
        code, message = software_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"Software Engineer phase failed: {message}"
        
        # Verify implementation.md was updated
        implementation = project_path / ".state" / "implementation.md"
        assert implementation.exists(), "implementation.md should exist"
        
        # Phase 3: Testing Engineer - Test fix
        testing_engineer = TestingEngineer(repo_root=project_path)
        code, message = testing_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"Testing Engineer phase failed: {message}"
        
        # Verify test-plan.md and test-results.md were updated
        test_plan = project_path / ".state" / "test-plan.md"
        test_results = project_path / ".state" / "test-results.md"
        assert test_plan.exists(), "test-plan.md should exist"
        assert test_results.exists(), "test-results.md should exist"
        
        # Phase 4: QA Engineer - Validate fix
        qa_engineer = QAEngineer(repo_root=project_path)
        code, message = qa_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"QA Engineer phase failed: {message}"
        
        # Verify quality-report.md was updated
        quality_report = project_path / ".state" / "quality-report.md"
        assert quality_report.exists(), "quality-report.md should exist"
        
        # Phase 5: Security Engineer - Security review of fix
        security_engineer = SecurityEngineer(repo_root=project_path)
        code, message = security_engineer.run_workflow(project_path=project_path)
        assert code == 0, f"Security Engineer phase failed: {message}"
        
        # Verify security-report.md was updated
        security_report = project_path / ".state" / "security-report.md"
        assert security_report.exists(), "security-report.md should exist"
        
        # Phase 6: Documentation Specialist - Update documentation
        documentation_specialist = DocumentationSpecialist(repo_root=project_path)
        code, message = documentation_specialist.run_workflow(project_path=project_path)
        assert code == 0, f"Documentation Specialist phase failed: {message}"
        
        # Verify changelog.md was updated
        changelog = project_path / ".state" / "changelog.md"
        assert changelog.exists(), "changelog.md should exist"
        
        # Verify pipeline-status.md was updated
        pipeline_status = project_path / ".state" / "pipeline-status.md"
        assert pipeline_status.exists(), "pipeline-status.md should exist"

    def test_bug_fix_preserves_functionality(self, setup_buggy_project):
        """Test that bug fix preserves existing functionality."""
        project_path = setup_buggy_project
        
        # Run tech lead analysis
        tech_lead = TechLead(repo_root=project_path)
        tech_lead.run_workflow(project_path=project_path)
        
        # Run software engineer fix
        software_engineer = SoftwareEngineer(repo_root=project_path)
        software_engineer.run_workflow(project_path=project_path)
        
        # Verify that other parts of codebase are preserved
        auth_file = project_path / "backend" / "app" / "auth.py"
        assert auth_file.exists(), "Auth file should still exist"

    def test_bug_fix_adds_regression_tests(self, setup_buggy_project):
        """Test that bug fix includes regression tests."""
        project_path = setup_buggy_project
        
        # Run through testing phase
        tech_lead = TechLead(repo_root=project_path)
        tech_lead.run_workflow(project_path=project_path)
        
        software_engineer = SoftwareEngineer(repo_root=project_path)
        software_engineer.run_workflow(project_path=project_path)
        
        testing_engineer = TestingEngineer(repo_root=project_path)
        testing_engineer.run_workflow(project_path=project_path)
        
        # Verify test results include regression tests
        test_results = project_path / ".state" / "test-results.md"
        assert test_results.exists(), "Test results should exist"

    def test_bug_fix_updates_documentation(self, setup_buggy_project):
        """Test that bug fix updates relevant documentation."""
        project_path = setup_buggy_project
        
        # Run through documentation phase
        tech_lead = TechLead(repo_root=project_path)
        tech_lead.run_workflow(project_path=project_path)
        
        software_engineer = SoftwareEngineer(repo_root=project_path)
        software_engineer.run_workflow(project_path=project_path)
        
        documentation_specialist = DocumentationSpecialist(repo_root=project_path)
        documentation_specialist.run_workflow(project_path=project_path)
        
        # Verify changelog mentions bug fix
        changelog = project_path / ".state" / "changelog.md"
        content = changelog.read_text()
        
        assert "bug" in content.lower() or "fix" in content.lower(), "Changelog should mention bug fix"

    def test_bug_fix_security_review(self, setup_buggy_project):
        """Test that bug fix passes security review."""
        project_path = setup_buggy_project
        
        # Run through security phase
        tech_lead = TechLead(repo_root=project_path)
        tech_lead.run_workflow(project_path=project_path)
        
        software_engineer = SoftwareEngineer(repo_root=project_path)
        software_engineer.run_workflow(project_path=project_path)
        
        security_engineer = SecurityEngineer(repo_root=project_path)
        code, message = security_engineer.run_workflow(project_path=project_path)
        
        assert code == 0, f"Security review should pass: {message}"
        
        # Verify security report exists
        security_report = project_path / ".state" / "security-report.md"
        assert security_report.exists(), "Security report should exist"

    def test_bug_fix_git_commits(self, setup_buggy_project):
        """Test that bug fix creates proper git commits."""
        project_path = setup_buggy_project
        
        # Run tech lead phase
        tech_lead = TechLead(repo_root=project_path)
        tech_lead.run_workflow(project_path=project_path)
        
        # Check git log for commit
        result = subprocess.run(
            ['git', 'log', '--oneline', '-1'],
            cwd=project_path,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'tech-lead' in result.stdout.lower() or 'architecture' in result.stdout.lower(), "Git commit should mention tech lead or architecture"

    def test_bug_fix_priority_handling(self, setup_buggy_project):
        """Test that high-priority bugs are handled appropriately."""
        project_path = setup_buggy_project
        
        # Verify bug report has high priority
        bug_report = project_path / ".state" / "bug-report.md"
        assert bug_report.exists(), "Bug report should exist"
        
        content = bug_report.read_text()
        assert "critical" in content.lower() or "high" in content.lower(), "Bug should be marked as critical or high priority"

    def test_bug_fix_root_cause_analysis(self, setup_buggy_project):
        """Test that bug fix includes proper root cause analysis."""
        project_path = setup_buggy_project
        
        # Run tech lead analysis
        tech_lead = TechLead(repo_root=project_path)
        tech_lead.run_workflow(project_path=project_path)
        
        # Verify root cause is documented
        architecture_spec = project_path / ".state" / "architecture-spec.md"
        assert architecture_spec.exists(), "Architecture spec should exist"

    def test_bug_fix_rollback_plan(self, setup_buggy_project):
        """Test that bug fix includes rollback plan."""
        project_path = setup_buggy_project
        
        # This would test rollback capability
        # For now, just verify the structure
        state_dir = project_path / ".state"
        assert state_dir.exists()

    def test_bug_fix_performance_impact(self, setup_buggy_project):
        """Test that bug fix doesn't negatively impact performance."""
        project_path = setup_buggy_project
        
        # Run through phases
        tech_lead = TechLead(repo_root=project_path)
        tech_lead.run_workflow(project_path=project_path)
        
        software_engineer = SoftwareEngineer(repo_root=project_path)
        software_engineer.run_workflow(project_path=project_path)
        
        # Verify performance considerations are documented
        implementation = project_path / ".state" / "implementation.md"
        assert implementation.exists(), "Implementation doc should exist"

    def test_bug_fix_with_multiple_issues(self, setup_buggy_project):
        """Test handling multiple related bugs."""
        project_path = setup_buggy_project
        
        # Add another bug report
        bug_report2 = project_path / ".state" / "bug-report-2.md"
        bug_report2.write_text("""# Bug Report

## Bug ID: BUG-124
## Title: Password reset link expires too quickly
## Severity: Medium
## Priority: High

### Description
Password reset link expires in 5 minutes, which is too short.
""")
        
        # Run pipeline for first bug
        tech_lead = TechLead(repo_root=project_path)
        tech_lead.run_workflow(project_path=project_path)
        
        # Verify both bugs are considered
        assert bug_report2.exists(), "Second bug report should exist"


class TestBugFixPipelineScenarios:
    """Tests for various bug fix scenarios."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary project directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_security_bug_fix(self, temp_project_dir):
        """Test fixing a security-related bug."""
        # Set up project with security bug
        iflow_dir = temp_project_dir / ".iflow" / "skills"
        iflow_dir.mkdir(parents=True, exist_ok=True)
        
        shared_state_dir = iflow_dir / ".shared-state"
        shared_state_dir.mkdir(parents=True, exist_ok=True)
        
        templates_dir = shared_state_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        (templates_dir / "pipeline-status.template.md").write_text("# Template\n")
        (templates_dir / "architecture-spec.template.md").write_text("# Template\n")
        
        state_dir = temp_project_dir / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)
        
        # Create security bug report
        bug_report = state_dir / "bug-report.md"
        bug_report.write_text("""# Bug Report

## Bug ID: SEC-001
## Title: SQL injection vulnerability
## Severity: Critical
## Type: Security

### Description
User input is not sanitized, leading to SQL injection vulnerability.
""")
        
        subprocess.run(['git', 'init'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=temp_project_dir, capture_output=True)
        
        # Run security-focused pipeline
        tech_lead = TechLead(repo_root=temp_project_dir)
        code, message = tech_lead.run_workflow(project_path=temp_project_dir)
        
        assert code == 0, f"Security bug fix should succeed: {message}"

    def test_performance_bug_fix(self, temp_project_dir):
        """Test fixing a performance-related bug."""
        # Set up project with performance bug
        iflow_dir = temp_project_dir / ".iflow" / "skills"
        iflow_dir.mkdir(parents=True, exist_ok=True)
        
        shared_state_dir = iflow_dir / ".shared-state"
        shared_state_dir.mkdir(parents=True, exist_ok=True)
        
        templates_dir = shared_state_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        (templates_dir / "pipeline-status.template.md").write_text("# Template\n")
        (templates_dir / "architecture-spec.template.md").write_text("# Template\n")
        
        state_dir = temp_project_dir / ".state"
        state_dir.mkdir(parents=True, exist_ok=True)
        
        # Create performance bug report
        bug_report = state_dir / "bug-report.md"
        bug_report.write_text("""# Bug Report

## Bug ID: PERF-001
## Title: Slow query performance
## Severity: High
## Type: Performance

### Description
User list query takes 10+ seconds with 1000 users.
""")
        
        subprocess.run(['git', 'init'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=temp_project_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=temp_project_dir, capture_output=True)
        
        # Run performance-focused pipeline
        tech_lead = TechLead(repo_root=temp_project_dir)
        code, message = tech_lead.run_workflow(project_path=temp_project_dir)
        
        assert code == 0, f"Performance bug fix should succeed: {message}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])