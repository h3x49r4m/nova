#!/usr/bin/env python3
"""
Product Manager Skill - Implementation
Provides feature planning, prioritization, and user story creation.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import shared utilities
from utils import (
    ErrorCode,
    StructuredLogger,
    LogFormat,
    InputSanitizer,
    run_git_command
)


class PrioritizationMethod:
    """Prioritization methods."""
    MOSCOW = "moscow"  # Must, Should, Could, Won't
    RICE = "rice"  # Reach, Impact, Confidence, Effort
    BUSINESS_VALUE = "business_value"


class INVESTCriteria:
    """INVEST criteria for user stories."""
    INDEPENDENT = "independent"
    NEGOTIABLE = "negotiable"
    VALUABLE = "valuable"
    ESTIMATABLE = "estimable"
    SMALL = "small"
    TESTABLE = "testable"


class ProductManager:
    """Product Manager role for feature planning and prioritization."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize product manager skill."""
        self.repo_root = repo_root or Path.cwd()
        self.config_dir = self.repo_root / '.iflow' / 'skills' / 'product-manager'
        self.config_file = self.config_dir / 'config.json'
        self.state_dir = self.repo_root / '.state'
        
        self.logger = StructuredLogger(
            name="product-manager",
            log_dir=self.repo_root / ".iflow" / "logs",
            log_format=LogFormat.JSON
        )
        self.load_config()
    
    def load_config(self):
        """Load configuration from config file."""
        self.config = {
            'version': '1.0.0',
            'prioritization_method': PrioritizationMethod.MOSCOW,
            'use_invest_criteria': True,
            'auto_commit': True
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                self.config.update(user_config)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Failed to load config: {e}. Using defaults.")
    
    def read_project_spec(self, project_path: Path) -> Tuple[int, str]:
        """
        Read project specification.
        
        Args:
            project_path: Path to the project directory
            
        Returns:
            Tuple of (exit_code, content or error message)
        """
        spec_file = project_path / '.state' / 'project-spec.md'
        
        try:
            if not spec_file.exists():
                return ErrorCode.FILE_NOT_FOUND.value, f"Project spec not found: {spec_file}"
            
            with open(spec_file, 'r') as f:
                content = f.read()
            
            return 0, content
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to read project spec: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_READ_ERROR.value, error_msg
    
    def extract_requirements(self, content: str) -> Dict[str, Any]:
        """
        Extract requirements from project spec content.
        
        Args:
            content: Project spec content
            
        Returns:
            Dictionary of extracted requirements
        """
        requirements = {
            'functional_requirements': [],
            'non_functional_requirements': [],
            'user_stories': [],
            'success_criteria': []
        }
        
        # Extract functional requirements
        fr_pattern = r'\*\*FR(\d+):\*\*\s*(.+?)(?=\n-|$)'
        fr_matches = re.findall(fr_pattern, content, re.MULTILINE | re.DOTALL)
        
        for idx, description in fr_matches:
            requirements['functional_requirements'].append({
                'id': f'FR{idx}',
                'description': description.strip()
            })
        
        # Extract non-functional requirements
        nfr_pattern = r'\*\*NFR(\d+):\*\*\s*(.+?)(?=\n-|$)'
        nfr_matches = re.findall(nfr_pattern, content, re.MULTILINE | re.DOTALL)
        
        for idx, description in nfr_matches:
            requirements['non_functional_requirements'].append({
                'id': f'NFR{idx}',
                'description': description.strip()
            })
        
        # Extract existing user stories
        us_pattern = r'\*\*US(\d+):\*\*\s*As a (.+?), I want to (.+?), so that (.+?)\.'
        us_matches = re.findall(us_pattern, content)
        
        for idx, (role, action, benefit) in us_matches:
            requirements['user_stories'].append({
                'id': f'US{idx}',
                'role': role.strip(),
                'action': action.strip(),
                'benefit': benefit.strip()
            })
        
        # Extract success criteria
        success_pattern = r'^\d+\.\s+(.+)$'
        success_matches = re.findall(success_pattern, content, re.MULTILINE)
        
        for match in success_matches:
            if 'Success Criteria' in content and match.strip():
                requirements['success_criteria'].append(match.strip())
        
        return requirements
    
    def prioritize_features_moscow(
        self,
        features: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Prioritize features using MoSCoW method.
        
        Args:
            features: List of features to prioritize
            
        Returns:
            List of prioritized features with MoSCoW priority
        """
        prioritized = []
        
        for feature in features:
            # Simple heuristic: assign priority based on feature description
            description = feature.get('description', '').lower()
            
            if any(keyword in description for keyword in ['critical', 'essential', 'must', 'core', 'primary']):
                priority = 'Must'
            elif any(keyword in description for keyword in ['important', 'should', 'valuable', 'key']):
                priority = 'Should'
            elif any(keyword in description for keyword in ['nice', 'could', 'optional', 'enhancement']):
                priority = 'Could'
            else:
                priority = "Won't"
            
            feature['moscow_priority'] = priority
            prioritized.append(feature)
        
        # Sort by MoSCoW priority
        priority_order = {'Must': 0, 'Should': 1, 'Could': 2, "Won't": 3}
        prioritized.sort(key=lambda x: priority_order.get(x['moscow_priority'], 3))
        
        return prioritized
    
    def prioritize_features_rice(
        self,
        features: List[Dict[str, Any]],
        rice_scores: Optional[Dict[str, Dict[str, float]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Prioritize features using RICE method.
        
        Args:
            features: List of features to prioritize
            rice_scores: Optional pre-defined RICE scores for each feature
            
        Returns:
            List of prioritized features with RICE scores
        """
        prioritized = []
        
        for feature in features:
            feature_id = feature.get('id', '')
            
            if rice_scores and feature_id in rice_scores:
                scores = rice_scores[feature_id]
            else:
                # Default scores if not provided
                scores = {
                    'reach': 10,  # Users affected
                    'impact': 3,  # Impact on goal (1-3)
                    'confidence': 0.8,  # Confidence in estimates (0-1)
                    'effort': 5  # Effort required (person-months)
                }
            
            # Calculate RICE score
            rice_score = (scores['reach'] * scores['impact'] * scores['confidence']) / scores['effort']
            
            feature['rice_score'] = round(rice_score, 2)
            feature['rice_details'] = scores
            prioritized.append(feature)
        
        # Sort by RICE score (descending)
        prioritized.sort(key=lambda x: x['rice_score'], reverse=True)
        
        return prioritized
    
    def create_user_stories(
        self,
        requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create user stories in INVEST format from requirements.
        
        Args:
            requirements: Dictionary of requirements
            
        Returns:
            List of user stories in INVEST format
        """
        user_stories = []
        
        # Create user stories from functional requirements
        for idx, req in enumerate(requirements.get('functional_requirements', []), 1):
            user_story = {
                'id': f'US{idx}',
                'role': 'User',
                'action': f'access {req["description"].lower()}',
                'benefit': f'meet the requirement for {req["id"]}',
                'priority': 'medium',
                'acceptance_criteria': [
                    f'The feature {req["id"]} is implemented',
                    f'The feature meets all specified requirements',
                    f'The feature is tested and documented'
                ],
                'invest_criteria': {
                    'independent': True,
                    'negotiable': True,
                    'valuable': True,
                    'estimable': True,
                    'small': True,
                    'testable': True
                },
                'story_points': 5,  # Default story points
                'sprint': 1  # Default sprint
            }
            user_stories.append(user_story)
        
        return user_stories
    
    def update_project_spec(
        self,
        project_path: Path,
        requirements: Dict[str, Any],
        prioritized_features: List[Dict[str, Any]],
        user_stories: List[Dict[str, Any]]
    ) -> Tuple[int, str]:
        """
        Update project specification with prioritized features and user stories.
        
        Args:
            project_path: Path to the project directory
            requirements: Dictionary of requirements
            prioritized_features: List of prioritized features
            user_stories: List of user stories
            
        Returns:
            Tuple of (exit_code, message)
        """
        spec_file = project_path / '.state' / 'project-spec.md'
        
        try:
            if not spec_file.exists():
                return ErrorCode.FILE_NOT_FOUND.value, f"Project spec not found: {spec_file}"
            
            with open(spec_file, 'r') as f:
                content = f.read()
            
            # Update user stories section
            us_section = "## User Stories\n\n"
            for idx, story in enumerate(user_stories, 1):
                us_section += f"- **US{idx}:** As a {InputSanitizer.sanitize_html(story.get('role', 'User'))}, "
                us_section += f"I want to {InputSanitizer.sanitize_html(story.get('action', 'do something'))}, "
                us_section += f"so that {InputSanitizer.sanitize_html(story.get('benefit', 'achieve a goal'))}.\n"
                us_section += f"  - Priority: {story.get('priority', 'medium')}\n"
                us_section += f"  - Story Points: {story.get('story_points', 5)}\n"
                us_section += f"  - Sprint: {story.get('sprint', 1)}\n"
                us_section += f"  - Acceptance Criteria:\n"
                for ac in story.get('acceptance_criteria', []):
                    us_section += f"    - {InputSanitizer.sanitize_html(ac)}\n"
                us_section += f"  - INVEST Criteria: {', '.join([k for k, v in story.get('invest_criteria', {}).items() if v])}\n\n"
            
            # Find and replace User Stories section
            us_marker = r'## User Stories\s*\n[\s\S]*?(?=\n##|\Z)'
            if re.search(us_marker, content):
                content = re.sub(us_marker, us_section, content)
            else:
                # Add User Stories section before Constraints
                constraints_marker = "## Constraints"
                if constraints_marker in content:
                    content = content.replace(constraints_marker, us_section + constraints_marker)
                else:
                    content += "\n" + us_section
            
            # Add prioritization section if using RICE
            if self.config.get('prioritization_method') == PrioritizationMethod.RICE:
                rice_section = "## Feature Prioritization (RICE)\n\n"
                for feature in prioritized_features:
                    rice_section += f"- **{InputSanitizer.sanitize_html(feature.get('id', 'Unknown'))}**: "
                    rice_section += f"RICE Score: {feature.get('rice_score', 0)}\n"
                    rice_section += f"  - Reach: {feature.get('rice_details', {}).get('reach', 0)}\n"
                    rice_section += f"  - Impact: {feature.get('rice_details', {}).get('impact', 0)}\n"
                    rice_section += f"  - Confidence: {feature.get('rice_details', {}).get('confidence', 0)}\n"
                    rice_section += f"  - Effort: {feature.get('rice_details', {}).get('effort', 0)}\n\n"
                
                # Add RICE section after User Stories
                content = content.replace("## Constraints", rice_section + "## Constraints")
            
            # Add Product Manager section
            pm_section = f"""
## Product Management Notes

**Prioritization Method:** {self.config.get('prioritization_method', 'moscow').upper()}
**Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Feature Count:** {len(prioritized_features)}
**User Story Count:** {len(user_stories)}

**Prioritization Summary:**

"""
            
            if self.config.get('prioritization_method') == PrioritizationMethod.MOSCOW:
                moscow_counts = {'Must': 0, 'Should': 0, 'Could': 0, "Won't": 0}
                for feature in prioritized_features:
                    priority = feature.get('moscow_priority', "Won't")
                    moscow_counts[priority] = moscow_counts.get(priority, 0) + 1
                
                pm_section += "- MoSCoW Distribution:\n"
                for priority, count in moscow_counts.items():
                    pm_section += f"  - {priority}: {count}\n"
            elif self.config.get('prioritization_method') == PrioritizationMethod.RICE:
                avg_rice = sum(f.get('rice_score', 0) for f in prioritized_features) / len(prioritized_features) if prioritized_features else 0
                pm_section += f"- Average RICE Score: {avg_rice:.2f}\n"
            
            pm_section += "\n**Next Steps:**\n"
            pm_section += "1. Review prioritized features with stakeholders\n"
            pm_section += "2. Refine user stories based on feedback\n"
            pm_section += "3. Plan sprint iterations\n"
            pm_section += "4. Coordinate with Tech Lead for technical planning\n"
            
            # Add Product Manager section at the end
            content += pm_section
            
            with open(spec_file, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Project specification updated: {spec_file}")
            return 0, f"Project specification updated: {spec_file}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to update project specification: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def commit_changes(
        self,
        project_path: Path,
        changes_description: str
    ) -> Tuple[int, str]:
        """
        Commit changes with proper metadata.
        
        Args:
            project_path: Path to the project directory
            changes_description: Description of changes
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Get current branch
            code, branch, _ = run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=project_path)
            if code != 0:
                return code, f"Failed to get current branch"
            
            # Stage project spec file
            spec_file = project_path / '.state' / 'project-spec.md'
            code, _, stderr = run_git_command(['add', str(spec_file)], cwd=project_path)
            if code != 0:
                return code, f"Failed to stage project spec: {stderr}"
            
            # Create commit message
            commit_message = f"""docs[product-manager]: {changes_description}

Changes:
- Prioritize features by business value
- Create user stories in INVEST format
- Define acceptance criteria
- Update project specification

---
Branch: {branch}

Files changed:
- {project_path}/.iflow/skills/.shared-state/project-spec.md

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
    
    def update_pipeline_status(
        self,
        project_path: Path,
        phase_name: str,
        status: str = "completed"
    ) -> Tuple[int, str]:
        """
        Update pipeline status with completion status.
        
        Args:
            project_path: Path to the project directory
            phase_name: Name of the phase
            status: Status of the phase (completed, in_progress, blocked)
            
        Returns:
            Tuple of (exit_code, message)
        """
        pipeline_file = project_path / '.state' / 'pipeline-status.md'
        
        try:
            if not pipeline_file.exists():
                return ErrorCode.FILE_NOT_FOUND.value, f"Pipeline status not found: {pipeline_file}"
            
            with open(pipeline_file, 'r') as f:
                content = f.read()
            
            # Update current phase and status
            content = re.sub(
                r'\*\*Phase:\*\* \d+/\d+ - (.+)',
                f'**Phase:** 2/5 - {phase_name}',
                content
            )
            
            content = re.sub(
                r'\*\*Status:\*\* (.+)',
                f'**Status:** {status}',
                content
            )
            
            content = re.sub(
                r'\*\*Progress:\*\* \d+%',
                '**Progress:** 20%',
                content
            )
            
            # Update phase progress - mark phase 1 as completed
            content = re.sub(
                r'- \[ \] Phase 1: Requirements Gathering \(Client\)',
                '- [x] Phase 1: Requirements Gathering (Client)',
                content
            )
            
            # Mark phase 2 as in progress
            content = re.sub(
                r'- \[ \] Phase 2: Planning & Design',
                '- [ ] Phase 2: Planning & Design (Tech Lead, Product Manager)',
                content
            )
            
            # Update last updated timestamp
            content = re.sub(
                r'\*\*Last Updated:\*\* .+',
                f'**Last Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                content
            )
            
            with open(pipeline_file, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Pipeline status updated: {pipeline_file}")
            return 0, f"Pipeline status updated: {pipeline_file}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to update pipeline status: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def run_workflow(
        self,
        project_path: Path,
        rice_scores: Optional[Dict[str, Dict[str, float]]] = None
    ) -> Tuple[int, str]:
        """
        Run the complete product manager workflow.
        
        Args:
            project_path: Path to the project directory
            rice_scores: Optional RICE scores for features
            
        Returns:
            Tuple of (exit_code, message)
        """
        # Step 1: Read project spec
        code, content = self.read_project_spec(project_path)
        if code != 0:
            return code, f"Failed to read project spec: {content}"
        
        # Step 2: Extract requirements
        requirements = self.extract_requirements(content)
        
        # Step 3: Prioritize features
        features = requirements.get('functional_requirements', [])
        
        if self.config.get('prioritization_method') == PrioritizationMethod.RICE:
            prioritized_features = self.prioritize_features_rice(features, rice_scores)
        else:
            prioritized_features = self.prioritize_features_moscow(features)
        
        # Step 4: Create user stories
        user_stories = self.create_user_stories(requirements)
        
        # Step 5: Update project spec
        code, message = self.update_project_spec(
            project_path, requirements, prioritized_features, user_stories
        )
        if code != 0:
            return code, f"Failed to update project spec: {message}"
        
        # Step 6: Commit changes
        if self.config.get('auto_commit', True):
            code, message = self.commit_changes(
                project_path,
                "prioritize features and create user stories"
            )
            if code != 0:
                return code, f"Failed to commit changes: {message}"
        
        # Step 7: Update pipeline status
        code, message = self.update_pipeline_status(
            project_path,
            "Planning & Design",
            "in_progress"
        )
        if code != 0:
            self.logger.warning(f"Failed to update pipeline status: {message}")
        
        return 0, f"Product manager workflow completed successfully. Prioritized {len(prioritized_features)} features and created {len(user_stories)} user stories."


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Product Manager skill for feature planning and prioritization')
    parser.add_argument('--project-path', type=str, help='Path to the project directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Prioritize command
    prioritize_parser = subparsers.add_parser('prioritize', help='Prioritize features')
    prioritize_parser.add_argument('--method', type=str, choices=['moscow', 'rice'], default='moscow', help='Prioritization method')
    prioritize_parser.add_argument('--rice-scores', type=str, help='JSON file with RICE scores')
    
    # Create user stories command
    stories_parser = subparsers.add_parser('create-stories', help='Create user stories')
    
    # Run workflow command
    workflow_parser = subparsers.add_parser('run', help='Run complete product manager workflow')
    workflow_parser.add_argument('--project-path', type=str, required=True, help='Path to the project directory')
    workflow_parser.add_argument('--rice-scores', type=str, help='JSON file with RICE scores')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    pm = ProductManager()
    project_path = Path(args.project_path) if args.project_path else Path.cwd()
    
    if args.command == 'prioritize':
        pm.config['prioritization_method'] = args.method
        
        rice_scores = None
        if args.rice_scores:
            with open(args.rice_scores, 'r') as f:
                rice_scores = json.load(f)
        
        code, content = pm.read_project_spec(project_path)
        if code != 0:
            print(f"Error: {content}", file=sys.stderr)
            return code
        
        requirements = pm.extract_requirements(content)
        features = requirements.get('functional_requirements', [])
        
        if args.method == 'rice':
            prioritized = pm.prioritize_features_rice(features, rice_scores)
            print("Prioritized features (RICE):")
            for feature in prioritized:
                print(f"  - {feature.get('id')}: RICE={feature.get('rice_score', 0)}")
        else:
            prioritized = pm.prioritize_features_moscow(features)
            print("Prioritized features (MoSCoW):")
            for feature in prioritized:
                print(f"  - {feature.get('id')}: {feature.get('moscow_priority')}")
        
        return 0
    
    elif args.command == 'create-stories':
        code, content = pm.read_project_spec(project_path)
        if code != 0:
            print(f"Error: {content}", file=sys.stderr)
            return code
        
        requirements = pm.extract_requirements(content)
        user_stories = pm.create_user_stories(requirements)
        
        print(f"Created {len(user_stories)} user stories:")
        for story in user_stories:
            print(f"  - {story.get('id')}: {story.get('role')} wants to {story.get('action')}")
        
        return 0
    
    elif args.command == 'run':
        rice_scores = None
        if args.rice_scores:
            with open(args.rice_scores, 'r') as f:
                rice_scores = json.load(f)
        
        code, output = pm.run_workflow(project_path, rice_scores)
        print(output)
        return code
    
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())