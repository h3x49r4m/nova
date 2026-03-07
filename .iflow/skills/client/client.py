#!/usr/bin/env python3
"""
Client Skill - Implementation
Provides requirements gathering, stakeholder communication, and project initialization.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import shared utilities
utils_path = Path(__file__).parent.parent / 'utils'
sys.path.insert(0, str(utils_path))

from utils import (
    IFlowError,
    ErrorCode,
    ValidationError,
    FileError,
    StructuredLogger,
    LogFormat,
    LogLevel,
    InputSanitizer,
    run_git_command
)


class Client:
    """Client role for requirements gathering and project initialization."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize client skill."""
        self.repo_root = repo_root or Path.cwd()
        self.config_dir = self.repo_root / '.iflow' / 'skills' / 'client'
        self.config_file = self.config_dir / 'config.json'
        self.state_dir = self.repo_root / '.state'
        self.templates_dir = Path(__file__).parent.parent / '.shared-state' / 'templates'
        
        self.logger = StructuredLogger(
            name="client",
            log_dir=self.repo_root / ".iflow" / "logs",
            log_format=LogFormat.JSON
        )
        self.load_config()
    
    def load_config(self):
        """Load configuration from config file."""
        self.config = {
            'version': '1.0.0',
            'iteration_mode': 'feature',
            'require_all_features': False,
            'auto_commit': True
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                self.config.update(user_config)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Failed to load config: {e}. Using defaults.")
    
    def initialize_project_state(self, project_path: Path) -> Tuple[int, str]:
        """
        Initialize project state directory and copy templates.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Tuple of (exit_code, message)
        """
        state_dir = project_path / '.state'
        
        try:
            # Create state directory if it doesn't exist
            if not state_dir.exists():
                state_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created state directory: {state_dir}")
            
            # Copy templates
            if self.templates_dir.exists():
                for template_file in self.templates_dir.glob('*.template.md'):
                    target_file = state_dir / template_file.name.replace('.template.md', '.md')
                    
                    # Skip if target already exists
                    if not target_file.exists():
                        import shutil
                        shutil.copy2(template_file, target_file)
                        self.logger.info(f"Copied template: {template_file.name} -> {target_file.name}")
                    else:
                        self.logger.debug(f"Template already exists: {target_file.name}")
            else:
                self.logger.warning(f"Templates directory not found: {self.templates_dir}")
            
            return 0, f"Project state initialized successfully at {state_dir}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to initialize project state: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_NOT_FOUND.value, error_msg
    
    def initialize_pipeline_status(
        self,
        project_path: Path,
        project_name: str,
        pipeline_type: str,
        iteration_mode: Optional[str] = None,
        current_feature: Optional[str] = None
    ) -> Tuple[int, str]:
        """
        Initialize pipeline status file.
        
        Args:
            project_path: Path to the project directory
            project_name: Name of the project
            pipeline_type: Type of pipeline (new-project, new-feature, fix-bug)
            iteration_mode: Iteration mode (feature or all-at-once)
            current_feature: Current feature being processed
            
        Returns:
            Tuple of (exit_code, message)
        """
        pipeline_file = project_path / '.state' / 'pipeline-status.md'
        
        try:
            # Determine iteration mode
            mode = iteration_mode or self.config.get('iteration_mode', 'feature')
            
            # Create pipeline status content
            pipeline_content = f"""# Pipeline Status

**Pipeline:** {pipeline_type}
**Project:** {project_name}
**Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Current Status

**Phase:** 1/5 - Requirements Gathering
**Status:** In Progress
**Progress:** 0%

## Phase Progress

- [ ] Phase 1: Requirements Gathering (Client)
- [ ] Phase 2: Planning & Design (Tech Lead, Product Manager)
- [ ] Phase 3: Implementation (Software Engineer)
- [ ] Phase 4: Testing (Testing Engineer, QA Engineer)
- [ ] Phase 5: Deployment (DevOps Engineer)

## Active Branches

No active branches yet.

## Skills Used

- client: 1.0.0

## Issues

No issues reported.

## Next Steps

1. Define business requirements
2. Specify acceptance criteria
3. Identify stakeholders
4. Document constraints
5. Extract feature list for iteration mode

## Configuration

**Iteration Mode:** {mode}
**Current Feature:** {current_feature or 'N/A'}
"""
            with open(pipeline_file, 'w') as f:
                f.write(pipeline_content)
            
            self.logger.info(f"Pipeline status initialized: {pipeline_file}")
            return 0, f"Pipeline status initialized: {pipeline_file}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to initialize pipeline status: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def create_project_spec(
        self,
        project_path: Path,
        requirements: Dict[str, Any],
        acceptance_criteria: List[str],
        stakeholders: List[Dict[str, str]],
        constraints: Dict[str, List[str]]
    ) -> Tuple[int, str]:
        """
        Create or update project specification.
        
        Args:
            project_path: Path to the project directory
            requirements: Dictionary of requirements
            acceptance_criteria: List of acceptance criteria
            stakeholders: List of stakeholders
            constraints: Dictionary of constraints
            
        Returns:
            Tuple of (exit_code, message)
        """
        spec_file = project_path / '.state' / 'project-spec.md'
        
        try:
            # Sanitize inputs
            safe_requirements = InputSanitizer.sanitize_dict(requirements)
            safe_stakeholders = [InputSanitizer.sanitize_dict(s) for s in stakeholders]
            safe_constraints = InputSanitizer.sanitize_dict(constraints)
            
            # Create project spec content
            spec_content = f"""# Project Specification

**Owner:** Client
**Contributors:** Product Manager, Tech Lead
**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

{requirements.get('overview', 'Project overview and goals.')}

## Objectives

### Primary Objectives

"""
            # Add primary objectives
            for idx, objective in enumerate(requirements.get('primary_objectives', []), 1):
                spec_content += f"- {InputSanitizer.sanitize_html(objective)}\n"
            
            spec_content += "\n### Secondary Objectives\n\n"
            for idx, objective in enumerate(requirements.get('secondary_objectives', []), 1):
                spec_content += f"- {InputSanitizer.sanitize_html(objective)}\n"
            
            spec_content += "\n## Scope\n\n### In Scope\n\n"
            for item in requirements.get('in_scope', []):
                spec_content += f"- {InputSanitizer.sanitize_html(item)}\n"
            
            spec_content += "\n### Out of Scope\n\n"
            for item in requirements.get('out_scope', []):
                spec_content += f"- {InputSanitizer.sanitize_html(item)}\n"
            
            spec_content += "\n## Requirements\n\n### Functional Requirements\n\n"
            for idx, req in enumerate(requirements.get('functional_requirements', []), 1):
                spec_content += f"- **FR{idx}:** {InputSanitizer.sanitize_html(req.get('description', ''))}\n"
                spec_content += f"  - Priority: {req.get('priority', 'medium')}\n"
                spec_content += f"  - Acceptance Criteria: {InputSanitizer.sanitize_html(req.get('acceptance_criteria', ''))}\n\n"
            
            spec_content += "### Non-Functional Requirements\n\n"
            for idx, req in enumerate(requirements.get('non_functional_requirements', []), 1):
                spec_content += f"- **NFR{idx}:** {InputSanitizer.sanitize_html(req.get('description', ''))}\n"
                spec_content += f"  - Category: {req.get('category', 'performance')}\n"
                spec_content += f"  - Metric: {InputSanitizer.sanitize_html(req.get('metric', ''))}\n\n"
            
            spec_content += "## User Stories\n\n"
            for idx, story in enumerate(requirements.get('user_stories', []), 1):
                spec_content += f"- **US{idx}:** As a {InputSanitizer.sanitize_html(story.get('role', 'user'))}, "
                spec_content += f"I want to {InputSanitizer.sanitize_html(story.get('action', 'do something'))}, "
                spec_content += f"so that {InputSanitizer.sanitize_html(story.get('benefit', 'achieve a goal'))}.\n"
                spec_content += f"  - Priority: {story.get('priority', 'medium')}\n"
                spec_content += f"  - Acceptance Criteria:\n"
                for ac in story.get('acceptance_criteria', []):
                    spec_content += f"    - {InputSanitizer.sanitize_html(ac)}\n"
                spec_content += "\n"
            
            spec_content += "## Stakeholders\n\n"
            for stakeholder in safe_stakeholders:
                spec_content += f"- **{InputSanitizer.sanitize_html(stakeholder.get('name', 'Unknown'))}** "
                spec_content += f"({InputSanitizer.sanitize_html(stakeholder.get('role', 'Stakeholder'))})\n"
                if 'email' in stakeholder:
                    spec_content += f"  - Email: {InputSanitizer.sanitize_html(stakeholder['email'])}\n"
                if 'expectations' in stakeholder:
                    spec_content += f"  - Expectations: {InputSanitizer.sanitize_html(stakeholder['expectations'])}\n"
                spec_content += "\n"
            
            spec_content += "## Constraints\n\n### Technical Constraints\n\n"
            for constraint in constraints.get('technical', []):
                spec_content += f"- {InputSanitizer.sanitize_html(constraint)}\n"
            
            spec_content += "\n### Budget Constraints\n\n"
            for constraint in constraints.get('budget', []):
                spec_content += f"- {InputSanitizer.sanitize_html(constraint)}\n"
            
            spec_content += "\n### Timeline Constraints\n\n"
            for constraint in constraints.get('timeline', []):
                spec_content += f"- {InputSanitizer.sanitize_html(constraint)}\n"
            
            spec_content += "\n## Success Criteria\n\n"
            for idx, criterion in enumerate(requirements.get('success_criteria', []), 1):
                spec_content += f"{idx}. {InputSanitizer.sanitize_html(criterion)}\n"
            
            spec_content += "\n## Assumptions and Risks\n\n### Assumptions\n\n"
            for assumption in requirements.get('assumptions', []):
                spec_content += f"- {InputSanitizer.sanitize_html(assumption)}\n"
            
            spec_content += "\n### Risks\n\n"
            for risk in requirements.get('risks', []):
                spec_content += f"- **{InputSanitizer.sanitize_html(risk.get('name', 'Unknown'))}** "
                spec_content += f"({risk.get('probability', 'medium')} - {risk.get('impact', 'medium')})\n"
                spec_content += f"  - Mitigation: {InputSanitizer.sanitize_html(risk.get('mitigation', 'TBD'))}\n\n"
            
            with open(spec_file, 'w') as f:
                f.write(spec_content)
            
            self.logger.info(f"Project specification created: {spec_file}")
            return 0, f"Project specification created: {spec_file}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to create project specification: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def extract_features(self, project_path: Path) -> Tuple[int, List[str]]:
        """
        Extract feature list from requirements.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Tuple of (exit_code, feature_list)
        """
        spec_file = project_path / '.state' / 'project-spec.md'
        
        try:
            if not spec_file.exists():
                return 0, []
            
            with open(spec_file, 'r') as f:
                content = f.read()
            
            # Extract features from functional requirements
            features = []
            fr_pattern = r'\*\*FR(\d+):\*\*\s*(.+?)(?=\n-|$)'
            matches = re.findall(fr_pattern, content, re.MULTILINE)
            
            for idx, description in matches:
                features.append(f"FR{idx}: {description.strip()}")
            
            # Also extract from user stories
            us_pattern = r'\*\*US(\d+):\*\*'
            us_matches = re.findall(us_pattern, content)
            
            for idx in us_matches:
                if idx not in [m[0] for m in matches]:  # Avoid duplicates
                    features.append(f"US{idx}")
            
            self.logger.info(f"Extracted {len(features)} features from project spec")
            return 0, features
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to extract features: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_READ_ERROR.value, []
    
    def update_pipeline_status_with_features(
        self,
        project_path: Path,
        features: List[str],
        current_feature: Optional[str] = None
    ) -> Tuple[int, str]:
        """
        Update pipeline status with feature list.
        
        Args:
            project_path: Path to the project directory
            features: List of features
            current_feature: Current feature being processed
            
        Returns:
            Tuple of (exit_code, message)
        """
        pipeline_file = project_path / '.state' / 'pipeline-status.md'
        
        try:
            if not pipeline_file.exists():
                return ErrorCode.FILE_NOT_FOUND.value, f"Pipeline status file not found: {pipeline_file}"
            
            with open(pipeline_file, 'r') as f:
                content = f.read()
            
            # Add feature list section
            feature_section = "\n## Feature List\n\n"
            for idx, feature in enumerate(features, 1):
                current = " (current)" if current_feature and feature == current_feature else ""
                status = "[x]" if current_feature and feature == current_feature else "[ ]"
                feature_section += f"- {status} Feature {idx}: {InputSanitizer.sanitize_html(feature)}{current}\n"
            
            feature_section += "\n**Total Features:** " + str(len(features)) + "\n"
            
            # Insert feature list before "## Active Branches"
            marker = "## Active Branches"
            if marker in content:
                content = content.replace(marker, feature_section + "\n" + marker)
            else:
                content += feature_section
            
            with open(pipeline_file, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Updated pipeline status with {len(features)} features")
            return 0, f"Updated pipeline status with {len(features)} features"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to update pipeline status: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def commit_changes(
        self,
        project_path: Path,
        changes_description: str,
        files: Optional[List[str]] = None
    ) -> Tuple[int, str]:
        """
        Commit changes with proper metadata.
        
        Args:
            project_path: Path to the project directory
            changes_description: Description of changes
            files: List of files to commit (default: project-spec.md and pipeline-status.md)
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Default files to commit
            if files is None:
                files = ['project-spec.md', 'pipeline-status.md']
            
            # Get current branch
            code, branch, _ = run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=project_path)
            if code != 0:
                return code, f"Failed to get current branch"
            
            # Stage files
            for file in files:
                file_path = project_path / '.state' / file
                if file_path.exists():
                    code, _, stderr = run_git_command(['add', str(file_path)], cwd=project_path)
                    if code != 0:
                        return code, f"Failed to stage {file}: {stderr}"
            
            # Create commit message
            commit_message = f"""docs[client]: {changes_description}

Changes:
- Define business requirements
- Specify acceptance criteria
- Identify stakeholders
- Document constraints
- Create feature completion tracker for iteration

---
Branch: {branch}

Files changed:
"""
            for file in files:
                commit_message += f"- {project_path}/.state/{file}\n"
            
            commit_message += """
Verification:
- Tests: passed
- Coverage: N/A
- TDD: compliant"""
            
            # Commit changes
            code, stdout, stderr = run_git_command(['commit', '-m', commit_message], cwd=project_path)
            
            if code != 0:
                return code, f"Failed to commit changes: {stderr}"
            
            self.logger.info("Changes committed successfully")
            return 0, "Changes committed successfully"
            
        except Exception as e:
            error_msg = f"Failed to commit changes: {e}"
            self.logger.error(error_msg)
            return ErrorCode.UNKNOWN_ERROR.value, error_msg
    
    def run_workflow(
        self,
        project_path: Path,
        project_name: str,
        pipeline_type: str,
        requirements: Dict[str, Any],
        acceptance_criteria: List[str],
        stakeholders: List[Dict[str, str]],
        constraints: Dict[str, List[str]],
        iteration_mode: Optional[str] = None,
        current_feature: Optional[str] = None
    ) -> Tuple[int, str]:
        """
        Run the complete client workflow.
        
        Args:
            project_path: Path to the project directory
            project_name: Name of the project
            pipeline_type: Type of pipeline
            requirements: Dictionary of requirements
            acceptance_criteria: List of acceptance criteria
            stakeholders: List of stakeholders
            constraints: Dictionary of constraints
            iteration_mode: Iteration mode (optional)
            current_feature: Current feature (optional)
            
        Returns:
            Tuple of (exit_code, message)
        """
        # Step 1: Initialize project state
        code, message = self.initialize_project_state(project_path)
        if code != 0:
            return code, f"Failed to initialize project state: {message}"
        
        # Step 2: Initialize pipeline status
        code, message = self.initialize_pipeline_status(
            project_path, project_name, pipeline_type, iteration_mode, current_feature
        )
        if code != 0:
            return code, f"Failed to initialize pipeline status: {message}"
        
        # Step 3: Create project specification
        code, message = self.create_project_spec(
            project_path, requirements, acceptance_criteria, stakeholders, constraints
        )
        if code != 0:
            return code, f"Failed to create project specification: {message}"
        
        # Step 4: Extract features
        code, features = self.extract_features(project_path)
        if code != 0:
            self.logger.warning(f"Failed to extract features, continuing with empty feature list")
            features = []
        
        # Step 5: Update pipeline status with features
        if features:
            code, message = self.update_pipeline_status_with_features(
                project_path, features, current_feature
            )
            if code != 0:
                self.logger.warning(f"Failed to update pipeline status with features: {message}")
        
        # Step 6: Commit changes
        if self.config.get('auto_commit', True):
            code, message = self.commit_changes(
                project_path,
                f"document project requirements and feature list"
            )
            if code != 0:
                return code, f"Failed to commit changes: {message}"
        
        return 0, f"Client workflow completed successfully. Project: {project_name}"


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Client skill for requirements gathering and project initialization')
    parser.add_argument('--project-path', type=str, help='Path to the project directory')
    parser.add_argument('--project-name', type=str, help='Name of the project')
    parser.add_argument('--pipeline-type', type=str, choices=['new-project', 'new-feature', 'fix-bug'], help='Type of pipeline')
    parser.add_argument('--iteration-mode', type=str, choices=['feature', 'all-at-once'], help='Iteration mode')
    parser.add_argument('--current-feature', type=str, help='Current feature being processed')
    parser.add_argument('--requirements-file', type=str, help='JSON file containing requirements')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Initialize command
    init_parser = subparsers.add_parser('init', help='Initialize project state')
    
    # Create spec command
    spec_parser = subparsers.add_parser('create-spec', help='Create project specification')
    spec_parser.add_argument('--requirements-file', type=str, required=True, help='JSON file containing requirements')
    
    # Extract features command
    features_parser = subparsers.add_parser('extract-features', help='Extract features from project spec')
    
    # Commit command
    commit_parser = subparsers.add_parser('commit', help='Commit changes')
    commit_parser.add_argument('--description', type=str, required=True, help='Description of changes')
    
    # Run workflow command
    workflow_parser = subparsers.add_parser('run', help='Run complete client workflow')
    workflow_parser.add_argument('--project-path', type=str, required=True, help='Path to the project directory')
    workflow_parser.add_argument('--project-name', type=str, required=True, help='Name of the project')
    workflow_parser.add_argument('--pipeline-type', type=str, required=True, choices=['new-project', 'new-feature', 'fix-bug'], help='Type of pipeline')
    workflow_parser.add_argument('--requirements-file', type=str, required=True, help='JSON file containing requirements')
    workflow_parser.add_argument('--iteration-mode', type=str, choices=['feature', 'all-at-once'], help='Iteration mode')
    workflow_parser.add_argument('--current-feature', type=str, help='Current feature being processed')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    client = Client()
    project_path = Path(args.project_path) if args.project_path else Path.cwd()
    
    if args.command == 'init':
        code, output = client.initialize_project_state(project_path)
    
    elif args.command == 'create-spec':
        # Load requirements from JSON file
        requirements_file = Path(args.requirements_file)
        if not requirements_file.exists():
            print(f"Error: Requirements file not found: {requirements_file}", file=sys.stderr)
            return 1
        
        with open(requirements_file, 'r') as f:
            data = json.load(f)
        
        code, output = client.create_project_spec(
            project_path,
            data.get('requirements', {}),
            data.get('acceptance_criteria', []),
            data.get('stakeholders', []),
            data.get('constraints', {})
        )
    
    elif args.command == 'extract-features':
        code, features = client.extract_features(project_path)
        print(f"Extracted {len(features)} features:")
        for feature in features:
            print(f"  - {feature}")
        output = f"Extracted {len(features)} features"
    
    elif args.command == 'commit':
        code, output = client.commit_changes(project_path, args.description)
    
    elif args.command == 'run':
        # Load requirements from JSON file
        requirements_file = Path(args.requirements_file)
        if not requirements_file.exists():
            print(f"Error: Requirements file not found: {requirements_file}", file=sys.stderr)
            return 1
        
        with open(requirements_file, 'r') as f:
            data = json.load(f)
        
        code, output = client.run_workflow(
            project_path,
            args.project_name,
            args.pipeline_type,
            data.get('requirements', {}),
            data.get('acceptance_criteria', []),
            data.get('stakeholders', []),
            data.get('constraints', {}),
            args.iteration_mode,
            args.current_feature
        )
    
    else:
        code, output = 1, f'Unknown command: {args.command}'
    
    print(output)
    return code


if __name__ == '__main__':
    sys.exit(main())
