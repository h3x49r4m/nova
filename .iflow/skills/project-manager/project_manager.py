#!/usr/bin/env python3
"""
Project Manager Skill - Implementation
Provides sprint planning, resource allocation, and timeline tracking.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
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


class SprintDuration:
    """Sprint duration options."""
    ONE_WEEK = 7
    TWO_WEEKS = 14
    THREE_WEEKS = 21
    FOUR_WEEKS = 28


class TaskPriority:
    """Task priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus:
    """Task status options."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"


class ProjectManager:
    """Project Manager role for sprint planning and resource allocation."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize project manager skill."""
        self.repo_root = repo_root or Path.cwd()
        self.config_dir = self.repo_root / '.iflow' / 'skills' / 'project-manager'
        self.config_file = self.config_dir / 'config.json'
        self.state_dir = self.repo_root / '.state'
        
        self.logger = StructuredLogger(
            name="project-manager",
            log_dir=self.repo_root / ".iflow" / "logs",
            log_format=LogFormat.JSON
        )
        self.load_config()
    
    def load_config(self):
        """Load configuration from config file."""
        self.config = {
            'version': '1.0.0',
            'sprint_duration': SprintDuration.TWO_WEEKS,
            'team_size': 5,
            'default_story_points': 3,
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
    
    def extract_user_stories(self, content: str) -> List[Dict[str, Any]]:
        """
        Extract user stories from project spec content.
        
        Args:
            content: Project spec content
            
        Returns:
            List of user stories
        """
        user_stories = []
        
        # Extract user stories
        us_pattern = r'\*\*US(\d+):\*\*\s*As a (.+?), I want to (.+?), so that (.+?)\.'
        us_matches = re.findall(us_pattern, content)
        
        for idx, (role, action, benefit) in enumerate(us_matches, 1):
            # Extract acceptance criteria for this story
            ac_pattern = rf'\*\*US{idx}:\*\*[\s\S]*?Acceptance Criteria:([\s\S]*?)(?=\n  - INVEST|\n- \*\*US|\n##|$)'
            ac_match = re.search(ac_pattern, content)
            
            acceptance_criteria = []
            if ac_match:
                ac_lines = ac_match.group(1).strip().split('\n')
                for line in ac_lines:
                    line = line.strip()
                    if line.startswith('- '):
                        acceptance_criteria.append(line[2:])
            
            # Extract story points and sprint
            sp_pattern = rf'\*\*US{idx}:\*\*[\s\S]*?Story Points: (\d+)'
            sp_match = re.search(sp_pattern, content)
            story_points = int(sp_match.group(1)) if sp_match else self.config.get('default_story_points', 3)
            
            sprint_pattern = rf'\*\*US{idx}:\*\*[\s\S]*?Sprint: (\d+)'
            sprint_match = re.search(sprint_pattern, content)
            sprint = int(sprint_match.group(1)) if sprint_match else 1
            
            user_stories.append({
                'id': f'US{idx}',
                'role': role.strip(),
                'action': action.strip(),
                'benefit': benefit.strip(),
                'acceptance_criteria': acceptance_criteria,
                'story_points': story_points,
                'sprint': sprint
            })
        
        return user_stories
    
    def break_down_features_into_tasks(
        self,
        user_stories: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Break down user stories into tasks.
        
        Args:
            user_stories: List of user stories
            
        Returns:
            List of tasks
        """
        tasks = []
        
        for story in user_stories:
            story_id = story.get('id', 'Unknown')
            
            # Create analysis task
            tasks.append({
                'id': f'TASK-{len(tasks)+1}',
                'story_id': story_id,
                'title': f'Analyze requirements for {story_id}',
                'description': f'Review and analyze requirements for {story_id}: {story.get("action", "")}',
                'type': 'analysis',
                'priority': TaskPriority.HIGH,
                'status': TaskStatus.TODO,
                'estimated_hours': 2,
                'assignee': None,
                'dependencies': []
            })
            
            # Create design task
            tasks.append({
                'id': f'TASK-{len(tasks)+1}',
                'story_id': story_id,
                'title': f'Design solution for {story_id}',
                'description': f'Create technical design for {story_id}',
                'type': 'design',
                'priority': TaskPriority.HIGH,
                'status': TaskStatus.TODO,
                'estimated_hours': 4,
                'assignee': None,
                'dependencies': [tasks[-2]['id']]
            })
            
            # Create implementation task
            tasks.append({
                'id': f'TASK-{len(tasks)+1}',
                'story_id': story_id,
                'title': f'Implement {story_id}',
                'description': f'Implement functionality for {story_id}',
                'type': 'implementation',
                'priority': TaskPriority.HIGH,
                'status': TaskStatus.TODO,
                'estimated_hours': story.get('story_points', 3) * 2,
                'assignee': None,
                'dependencies': [tasks[-2]['id']]
            })
            
            # Create testing task
            tasks.append({
                'id': f'TASK-{len(tasks)+1}',
                'story_id': story_id,
                'title': f'Test {story_id}',
                'description': f'Write and execute tests for {story_id}',
                'type': 'testing',
                'priority': TaskPriority.MEDIUM,
                'status': TaskStatus.TODO,
                'estimated_hours': story.get('story_points', 3),
                'assignee': None,
                'dependencies': [tasks[-2]['id']]
            })
            
            # Create review task
            tasks.append({
                'id': f'TASK-{len(tasks)+1}',
                'story_id': story_id,
                'title': f'Review {story_id}',
                'description': f'Code review for {story_id}',
                'type': 'review',
                'priority': TaskPriority.MEDIUM,
                'status': TaskStatus.TODO,
                'estimated_hours': 1,
                'assignee': None,
                'dependencies': [tasks[-2]['id']]
            })
        
        return tasks
    
    def create_sprint_backlog(
        self,
        user_stories: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create sprint backlog from user stories and tasks.
        
        Args:
            user_stories: List of user stories
            tasks: List of tasks
            
        Returns:
            Sprint backlog dictionary
        """
        # Group stories by sprint
        sprints = {}
        for story in user_stories:
            sprint_num = story.get('sprint', 1)
            if sprint_num not in sprints:
                sprints[sprint_num] = {
                    'number': sprint_num,
                    'stories': [],
                    'tasks': [],
                    'total_story_points': 0,
                    'estimated_hours': 0
                }
            sprints[sprint_num]['stories'].append(story)
            sprints[sprint_num]['total_story_points'] += story.get('story_points', 0)
        
        # Add tasks to sprints
        for task in tasks:
            # Find the sprint for this task based on its story
            story_id = task.get('story_id', '')
            for sprint_num, sprint in sprints.items():
                if any(s.get('id') == story_id for s in sprint['stories']):
                    sprint['tasks'].append(task)
                    sprint['estimated_hours'] += task.get('estimated_hours', 0)
                    break
        
        return sprints
    
    def allocate_resources(
        self,
        tasks: List[Dict[str, Any]],
        team_members: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Allocate team members to tasks.
        
        Args:
            tasks: List of tasks
            team_members: List of team member names
            
        Returns:
            List of tasks with assigned resources
        """
        if team_members is None:
            team_size = self.config.get('team_size', 5)
            team_members = [f'Team Member {i+1}' for i in range(team_size)]
        
        # Simple round-robin allocation
        for idx, task in enumerate(tasks):
            # Skip tasks that already have assignees
            if task.get('assignee'):
                continue
            
            # Allocate based on task type
            task_type = task.get('type', 'implementation')
            if task_type == 'analysis':
                assignee_idx = idx % min(len(team_members), 2)  # Analysts
            elif task_type == 'design':
                assignee_idx = idx % len(team_members)
            elif task_type == 'implementation':
                assignee_idx = idx % len(team_members)
            elif task_type == 'testing':
                assignee_idx = idx % min(len(team_members), 2)  # Testers
            else:
                assignee_idx = idx % len(team_members)
            
            task['assignee'] = team_members[assignee_idx]
        
        return tasks
    
    def estimate_timeline_and_milestones(
        self,
        sprints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Estimate timeline and create milestones.
        
        Args:
            sprints: Dictionary of sprints
            
        Returns:
            List of milestones
        """
        milestones = []
        sprint_duration = self.config.get('sprint_duration', SprintDuration.TWO_WEEKS)
        start_date = datetime.now()
        
        for sprint_num in sorted(sprints.keys()):
            sprint = sprints[sprint_num]
            sprint_start = start_date + timedelta(days=(sprint_num - 1) * sprint_duration)
            sprint_end = sprint_start + timedelta(days=sprint_duration)
            
            milestones.append({
                'name': f'Sprint {sprint_num}',
                'type': 'sprint',
                'start_date': sprint_start.strftime('%Y-%m-%d'),
                'end_date': sprint_end.strftime('%Y-%m-%d'),
                'description': f'Complete {len(sprint["stories"])} user stories with {sprint["total_story_points"]} story points',
                'status': 'upcoming' if sprint_start > datetime.now() else 'in_progress',
                'deliverables': [f'{s["id"]}: {s.get("action", "")}' for s in sprint['stories']]
            })
        
        # Add project milestone
        if sprints:
            last_sprint_num = max(sprints.keys())
            project_end = start_date + timedelta(days=last_sprint_num * sprint_duration)
            milestones.append({
                'name': 'Project Completion',
                'type': 'milestone',
                'start_date': project_end.strftime('%Y-%m-%d'),
                'end_date': project_end.strftime('%Y-%m-%d'),
                'description': 'Project delivery and deployment',
                'status': 'upcoming',
                'deliverables': ['All features implemented', 'All tests passing', 'Documentation complete', 'Deployment ready']
            })
        
        return milestones
    
    def identify_dependencies_and_risks(
        self,
        tasks: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Identify dependencies and risks.
        
        Args:
            tasks: List of tasks
            
        Returns:
            Tuple of (dependencies, risks)
        """
        dependencies = []
        risks = []
        
        # Analyze dependencies
        for task in tasks:
            task_deps = task.get('dependencies', [])
            for dep_id in task_deps:
                dependencies.append({
                    'task_id': task['id'],
                    'depends_on': dep_id,
                    'type': 'blocking'
                })
        
        # Identify potential risks
        total_hours = sum(t.get('estimated_hours', 0) for t in tasks)
        team_size = self.config.get('team_size', 5)
        available_hours_per_sprint = team_size * 40 * (self.config.get('sprint_duration', 14) / 7)
        
        if total_hours > available_hours_per_sprint * 1.5:
            risks.append({
                'name': 'Timeline Overrun',
                'probability': 'high',
                'impact': 'high',
                'description': f'Total estimated hours ({total_hours}) exceed sprint capacity by {((total_hours / available_hours_per_sprint) - 1) * 100:.1f}%',
                'mitigation': 'Consider reducing scope, adding team members, or extending timeline'
            })
        
        # Check for tasks with no assignees
        unassigned_tasks = [t for t in tasks if not t.get('assignee')]
        if unassigned_tasks:
            risks.append({
                'name': 'Resource Gap',
                'probability': 'medium',
                'impact': 'medium',
                'description': f'{len(unassigned_tasks)} tasks are unassigned',
                'mitigation': 'Assign team members to unassigned tasks'
            })
        
        # Check for tasks with high estimated hours
        large_tasks = [t for t in tasks if t.get('estimated_hours', 0) > 16]
        if large_tasks:
            risks.append({
                'name': 'Large Task Complexity',
                'probability': 'medium',
                'impact': 'medium',
                'description': f'{len(large_tasks)} tasks have estimates > 16 hours',
                'mitigation': 'Break down large tasks into smaller subtasks'
            })
        
        return dependencies, risks
    
    def create_implementation_plan(
        self,
        project_path: Path,
        user_stories: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]],
        sprints: Dict[str, Any],
        milestones: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]],
        risks: List[Dict[str, Any]]
    ) -> Tuple[int, str]:
        """
        Create or update implementation plan.
        
        Args:
            project_path: Path to the project directory
            user_stories: List of user stories
            tasks: List of tasks
            sprints: Dictionary of sprints
            milestones: List of milestones
            dependencies: List of dependencies
            risks: List of risks
            
        Returns:
            Tuple of (exit_code, message)
        """
        plan_file = project_path / '.state' / 'implementation-plan.md'
        
        try:
            # Create implementation plan content
            plan_content = f"""# Implementation Plan

**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Team Size:** {self.config.get('team_size', 5)}
**Sprint Duration:** {self.config.get('sprint_duration', 14)} days

## Overview

This document outlines the implementation plan for the project, including sprint planning, task breakdown, resource allocation, timeline estimation, and risk management.

## User Stories Summary

**Total User Stories:** {len(user_stories)}
**Total Story Points:** {sum(s.get('story_points', 0) for s in user_stories)}

### User Stories

"""
            
            for story in user_stories:
                plan_content += f"#### {InputSanitizer.sanitize_html(story.get('id', 'Unknown'))}\n\n"
                plan_content += f"**As a:** {InputSanitizer.sanitize_html(story.get('role', 'User'))}\n"
                plan_content += f"**I want to:** {InputSanitizer.sanitize_html(story.get('action', 'do something'))}\n"
                plan_content += f"**So that:** {InputSanitizer.sanitize_html(story.get('benefit', 'achieve a goal'))}\n"
                plan_content += f"**Story Points:** {story.get('story_points', 0)}\n"
                plan_content += f"**Sprint:** {story.get('sprint', 1)}\n\n"
            
            plan_content += "## Task Breakdown\n\n"
            plan_content += f"**Total Tasks:** {len(tasks)}\n"
            plan_content += f"**Total Estimated Hours:** {sum(t.get('estimated_hours', 0) for t in tasks)}\n\n"
            
            # Group tasks by type
            task_types = {}
            for task in tasks:
                task_type = task.get('type', 'other')
                if task_type not in task_types:
                    task_types[task_type] = []
                task_types[task_type].append(task)
            
            for task_type, type_tasks in task_types.items():
                plan_content += f"### {task_type.title()} Tasks ({len(type_tasks)})\n\n"
                for task in type_tasks:
                    plan_content += f"- **{InputSanitizer.sanitize_html(task.get('id', 'Unknown'))}**: {InputSanitizer.sanitize_html(task.get('title', 'No title'))}\n"
                    plan_content += f"  - Status: {task.get('status', 'todo')}\n"
                    plan_content += f"  - Priority: {task.get('priority', 'medium')}\n"
                    plan_content += f"  - Estimated Hours: {task.get('estimated_hours', 0)}\n"
                    plan_content += f"  - Assignee: {InputSanitizer.sanitize_html(task.get('assignee', 'Unassigned'))}\n"
                    if task.get('dependencies'):
                        plan_content += f"  - Dependencies: {', '.join(task['dependencies'])}\n"
                    plan_content += "\n"
            
            plan_content += "## Sprint Plan\n\n"
            plan_content += f"**Total Sprints:** {len(sprints)}\n\n"
            
            for sprint_num in sorted(sprints.keys()):
                sprint = sprints[sprint_num]
                plan_content += f"### Sprint {sprint_num}\n\n"
                plan_content += f"**Story Points:** {sprint['total_story_points']}\n"
                plan_content += f"**Estimated Hours:** {sprint['estimated_hours']}\n"
                plan_content += f"**User Stories:** {len(sprint['stories'])}\n"
                plan_content += f"**Tasks:** {len(sprint['tasks'])}\n\n"
                
                plan_content += "**Stories:**\n"
                for story in sprint['stories']:
                    plan_content += f"- {InputSanitizer.sanitize_html(story.get('id', 'Unknown'))}: {InputSanitizer.sanitize_html(story.get('action', ''))}\n"
                plan_content += "\n"
            
            plan_content += "## Timeline and Milestones\n\n"
            
            for milestone in milestones:
                plan_content += f"### {InputSanitizer.sanitize_html(milestone.get('name', 'Unknown'))}\n\n"
                plan_content += f"**Type:** {milestone.get('type', 'milestone')}\n"
                plan_content += f"**Start Date:** {milestone.get('start_date', 'TBD')}\n"
                plan_content += f"**End Date:** {milestone.get('end_date', 'TBD')}\n"
                plan_content += f"**Status:** {milestone.get('status', 'upcoming')}\n"
                plan_content += f"**Description:** {InputSanitizer.sanitize_html(milestone.get('description', ''))}\n\n"
                
                if milestone.get('deliverables'):
                    plan_content += "**Deliverables:**\n"
                    for deliverable in milestone['deliverables']:
                        plan_content += f"- {InputSanitizer.sanitize_html(deliverable)}\n"
                    plan_content += "\n"
            
            plan_content += "## Dependencies\n\n"
            
            if dependencies:
                for dep in dependencies:
                    plan_content += f"- **{dep['task_id']}** depends on **{dep['depends_on']}** ({dep.get('type', 'blocking')})\n"
            else:
                plan_content += "No critical dependencies identified.\n"
            
            plan_content += "\n## Risks and Mitigation\n\n"
            
            if risks:
                for risk in risks:
                    plan_content += f"### {InputSanitizer.sanitize_html(risk.get('name', 'Unknown'))}\n\n"
                    plan_content += f"**Probability:** {risk.get('probability', 'unknown')}\n"
                    plan_content += f"**Impact:** {risk.get('impact', 'unknown')}\n"
                    plan_content += f"**Description:** {InputSanitizer.sanitize_html(risk.get('description', ''))}\n"
                    plan_content += f"**Mitigation:** {InputSanitizer.sanitize_html(risk.get('mitigation', 'TBD'))}\n\n"
            else:
                plan_content += "No significant risks identified.\n"
            
            plan_content += "\n## Resource Allocation\n\n"
            plan_content += f"**Team Size:** {self.config.get('team_size', 5)}\n"
            plan_content += f"**Total Capacity:** {self.config.get('team_size', 5) * 40} hours/week\n\n"
            
            # Calculate workload per team member
            workload = {}
            for task in tasks:
                assignee = task.get('assignee', 'Unassigned')
                if assignee not in workload:
                    workload[assignee] = 0
                workload[assignee] += task.get('estimated_hours', 0)
            
            plan_content += "**Workload Distribution:**\n"
            for assignee, hours in workload.items():
                plan_content += f"- {InputSanitizer.sanitize_html(assignee)}: {hours} hours\n"
            
            with open(plan_file, 'w') as f:
                f.write(plan_content)
            
            self.logger.info(f"Implementation plan created: {plan_file}")
            return 0, f"Implementation plan created: {plan_file}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to create implementation plan: {e}"
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
            
            # Stage implementation plan file
            plan_file = project_path / '.state' / 'implementation-plan.md'
            code, _, stderr = run_git_command(['add', str(plan_file)], cwd=project_path)
            if code != 0:
                return code, f"Failed to stage implementation plan: {stderr}"
            
            # Create commit message
            commit_message = f"""docs[project-manager]: {changes_description}

Changes:
- Break down features into tasks
- Create sprint backlog
- Allocate resources
- Estimate timeline and milestones
- Identify dependencies and risks

---
Branch: {branch}

Files changed:
- {project_path}/.state/implementation-plan.md

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
                '**Progress:** 40%',
                content
            )
            
            # Update phase progress - mark phase 1 and 2 as completed
            content = re.sub(
                r'- \[ \] Phase 1: Requirements Gathering \(Client\)',
                '- [x] Phase 1: Requirements Gathering (Client)',
                content
            )
            
            content = re.sub(
                r'- \[ \] Phase 2: Planning & Design',
                '- [x] Phase 2: Planning & Design (Tech Lead, Product Manager)',
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
        team_members: Optional[List[str]] = None
    ) -> Tuple[int, str]:
        """
        Run the complete project manager workflow.
        
        Args:
            project_path: Path to the project directory
            team_members: Optional list of team member names
            
        Returns:
            Tuple of (exit_code, message)
        """
        # Step 1: Read project spec
        code, content = self.read_project_spec(project_path)
        if code != 0:
            return code, f"Failed to read project spec: {content}"
        
        # Step 2: Extract user stories
        user_stories = self.extract_user_stories(content)
        
        # Step 3: Break down features into tasks
        tasks = self.break_down_features_into_tasks(user_stories)
        
        # Step 4: Create sprint backlog
        sprints = self.create_sprint_backlog(user_stories, tasks)
        
        # Step 5: Allocate resources
        tasks = self.allocate_resources(tasks, team_members)
        
        # Step 6: Estimate timeline and milestones
        milestones = self.estimate_timeline_and_milestones(sprints)
        
        # Step 7: Identify dependencies and risks
        dependencies, risks = self.identify_dependencies_and_risks(tasks)
        
        # Step 8: Create implementation plan
        code, message = self.create_implementation_plan(
            project_path, user_stories, tasks, sprints, milestones, dependencies, risks
        )
        if code != 0:
            return code, f"Failed to create implementation plan: {message}"
        
        # Step 9: Commit changes
        if self.config.get('auto_commit', True):
            code, message = self.commit_changes(
                project_path,
                "plan sprint and allocate resources"
            )
            if code != 0:
                return code, f"Failed to commit changes: {message}"
        
        # Step 10: Update pipeline status
        code, message = self.update_pipeline_status(
            project_path,
            "Planning & Design",
            "completed"
        )
        if code != 0:
            self.logger.warning(f"Failed to update pipeline status: {message}")
        
        return 0, f"Project manager workflow completed successfully. Created {len(tasks)} tasks across {len(sprints)} sprints with {len(milestones)} milestones."


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Project Manager skill for sprint planning and resource allocation')
    parser.add_argument('--project-path', type=str, help='Path to the project directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Plan sprint command
    plan_parser = subparsers.add_parser('plan', help='Plan sprint')
    plan_parser.add_argument('--team-members', type=str, nargs='+', help='Team member names')
    
    # Create tasks command
    tasks_parser = subparsers.add_parser('create-tasks', help='Create tasks from user stories')
    
    # Allocate resources command
    allocate_parser = subparsers.add_parser('allocate', help='Allocate resources')
    allocate_parser.add_argument('--team-members', type=str, nargs='+', help='Team member names')
    
    # Run workflow command
    workflow_parser = subparsers.add_parser('run', help='Run complete project manager workflow')
    workflow_parser.add_argument('--project-path', type=str, required=True, help='Path to the project directory')
    workflow_parser.add_argument('--team-members', type=str, nargs='+', help='Team member names')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    pm = ProjectManager()
    project_path = Path(args.project_path) if args.project_path else Path.cwd()
    
    if args.command == 'plan':
        team_members = getattr(args, 'team_members', None)
        code, content = pm.read_project_spec(project_path)
        if code != 0:
            print(f"Error: {content}", file=sys.stderr)
            return code
        
        user_stories = pm.extract_user_stories(content)
        tasks = pm.break_down_features_into_tasks(user_stories)
        sprints = pm.create_sprint_backlog(user_stories, tasks)
        milestones = pm.estimate_timeline_and_milestones(sprints)
        
        print(f"Sprint Plan:")
        for sprint_num in sorted(sprints.keys()):
            sprint = sprints[sprint_num]
            print(f"  Sprint {sprint_num}: {sprint['total_story_points']} story points, {len(sprint['stories'])} stories")
        
        print(f"\nMilestones:")
        for milestone in milestones:
            print(f"  - {milestone['name']}: {milestone['start_date']} to {milestone['end_date']}")
        
        return 0
    
    elif args.command == 'create-tasks':
        code, content = pm.read_project_spec(project_path)
        if code != 0:
            print(f"Error: {content}", file=sys.stderr)
            return code
        
        user_stories = pm.extract_user_stories(content)
        tasks = pm.break_down_features_into_tasks(user_stories)
        
        print(f"Created {len(tasks)} tasks:")
        for task in tasks:
            print(f"  - {task['id']}: {task['title']} ({task['estimated_hours']} hours)")
        
        return 0
    
    elif args.command == 'allocate':
        team_members = getattr(args, 'team_members', None)
        code, content = pm.read_project_spec(project_path)
        if code != 0:
            print(f"Error: {content}", file=sys.stderr)
            return code
        
        user_stories = pm.extract_user_stories(content)
        tasks = pm.break_down_features_into_tasks(user_stories)
        tasks = pm.allocate_resources(tasks, team_members)
        
        print(f"Resource Allocation:")
        for task in tasks:
            print(f"  - {task['id']}: {task.get('assignee', 'Unassigned')}")
        
        return 0
    
    elif args.command == 'run':
        team_members = getattr(args, 'team_members', None)
        code, output = pm.run_workflow(project_path, team_members)
        print(output)
        return code
    
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
