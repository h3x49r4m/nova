#!/usr/bin/env python3
"""
Git-Flow Skill - Workflow Orchestration
Provides gate-based workflow with role-based branching, review/approval gates,
phase tracking, and reversible approvals. Delegates git operations to git-manage.
"""

import argparse
import json
import os
import sys
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from .pipeline_manager import PipelineUpdateManager

# Import shared git command utility
sys.path.insert(0, str(Path(__file__).parent.parent / 'utils'))
from utils import (
    run_git_command,
    get_current_branch,
    validate_branch_name,
    GitError,
    GitCommandTimeout,
    write_locked_json,
    read_locked_json,
    FileLockError,
    validate_workflow_state,
    validate_branch_state,
    SchemaValidationError,
    StructuredLogger,
    LogFormat,
    LogLevel,
    validate_json_schema,
    BranchStatus,
    PhaseStatus,
    WorkflowStatus
)
from utils import CheckpointManager, PrerequisiteChecker, validate_workflow_prerequisites, InputSanitizer


class ReviewEvent:
    def __init__(self, action: str, actor: str, comment: Optional[str] = None, 
                 reason: Optional[str] = None, merge_commit: Optional[str] = None):
        self.action = action
        self.actor = actor
        self.timestamp = datetime.now().isoformat()
        self.comment = comment
        self.reason = reason
        self.merge_commit = merge_commit
    
    def to_dict(self) -> Dict:
        return {
            "action": self.action,
            "actor": self.actor,
            "timestamp": self.timestamp,
            "comment": self.comment,
            "reason": self.reason,
            "merge_commit": self.merge_commit
        }


class BranchState:
    def __init__(self, name: str, role: str, phase: int):
        self.name = name
        self.role = role
        self.status = BranchStatus.PENDING
        self.phase = phase
        self.created_at = datetime.now().isoformat()
        self.commits: List[Dict] = []
        self.merge_commit: Optional[str] = None
        self.approved_by: Optional[str] = None
        self.approved_at: Optional[str] = None
        self.unapproved_by: Optional[str] = None
        self.unapproved_at: Optional[str] = None
        self.dependencies: List[str] = []
        self.dependents: List[str] = []
        self.review_history: List[Dict] = []
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
            "phase": self.phase,
            "created_at": self.created_at,
            "commits": self.commits,
            "merge_commit": self.merge_commit,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "unapproved_by": self.unapproved_by,
            "unapproved_at": self.unapproved_at,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "review_history": self.review_history,
            "_version": str(int(self._get_version_from_history())) if self.review_history else "0",
            "_modified": self._get_last_modified()
        }
    
    def _get_version_from_history(self) -> int:
        """Calculate version from review history."""
        return len(self.review_history)
    
    def _get_last_modified(self) -> str:
        """Get the last modification timestamp."""
        if self.review_history:
            return self.review_history[-1].get('timestamp', self.created_at)
        return self.created_at
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BranchState':
        branch = cls(data["name"], data["role"], data["phase"])
        branch.status = BranchStatus(data["status"])
        branch.created_at = data["created_at"]
        branch.commits = data.get("commits", [])
        branch.merge_commit = data.get("merge_commit")
        branch.approved_by = data.get("approved_by")
        branch.approved_at = data.get("approved_at")
        branch.unapproved_by = data.get("unapproved_by")
        branch.unapproved_at = data.get("unapproved_at")
        branch.dependencies = data.get("dependencies", [])
        branch.dependents = data.get("dependents", [])
        branch.review_history = data.get("review_history", [])
        return branch


class Phase:
    def __init__(self, name: str, role: str, order: int, required: bool):
        self.name = name
        self.role = role
        self.order = order
        self.required = required
        self.status = PhaseStatus.PENDING
        self.branch: Optional[str] = None
        self.dependencies: List[int] = []
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.timeout_seconds: int = 604800  # 7 days default
        self.timeout_warning_sent: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "role": self.role,
            "order": self.order,
            "required": self.required,
            "status": self.status.value,
            "branch": self.branch,
            "dependencies": self.dependencies,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "timeout_seconds": self.timeout_seconds,
            "timeout_warning_sent": self.timeout_warning_sent
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Phase':
        phase = cls(data["name"], data["role"], data["order"], data["required"])
        phase.status = PhaseStatus(data["status"])
        phase.branch = data.get("branch")
        phase.dependencies = data.get("dependencies", [])
        phase.started_at = data.get("started_at")
        phase.completed_at = data.get("completed_at")
        phase.timeout_seconds = data.get("timeout_seconds", 604800)
        phase.timeout_warning_sent = data.get("timeout_warning_sent", False)
        return phase

class WorkflowState:
    def __init__(self, feature: str):
        self.feature = feature
        self.status = WorkflowStatus.INITIALIZED
        self.current_phase = 0
        self.phases: List[Phase] = []
        self.branches: Dict[str, BranchState] = {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            "feature": self.feature,
            "status": self.status.value,
            "current_phase": self.current_phase,
            "phases": [p.to_dict() for p in self.phases],
            "branches": {k: v.to_dict() for k, v in self.branches.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "_version": str(self._calculate_version()),
            "_modified": self.updated_at
        }
    
    def _calculate_version(self) -> int:
        """Calculate workflow version based on changes."""
        # Base version from phases
        version = len(self.phases)
        
        # Add for each branch
        version += len(self.branches)
        
        # Add for workflow status changes
        if self.status != WorkflowStatus.INITIALIZED:
            version += 1
        
        # Add for phase transitions
        version += self.current_phase
        
        return version
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowState':
        workflow = cls(data["feature"])
        workflow.status = WorkflowStatus(data["status"])
        workflow.current_phase = data.get("current_phase", 0)
        workflow.phases = [Phase.from_dict(p) for p in data.get("phases", [])]
        workflow.branches = {k: BranchState.from_dict(v) for k, v in data.get("branches", {}).items()}
        workflow.created_at = data.get("created_at", datetime.now().isoformat())
        workflow.updated_at = data.get("updated_at", datetime.now().isoformat())
        return workflow


class DependencyGraph:
    """Manages branch dependency relationships."""
    
    def __init__(self):
        """Initialize an empty dependency graph."""
        self.graph: Dict[str, List[str]] = {}
        self.reverse_graph: Dict[str, List[str]] = {}
    
    def add_dependency(self, branch: str, depends_on: List[str]):
        """
        Add a dependency relationship between branches.
        
        Args:
            branch: Name of the branch that has dependencies
            depends_on: List of branch names that this branch depends on
        """
        if branch not in self.graph:
            self.graph[branch] = []
        if branch not in self.reverse_graph:
            self.reverse_graph[branch] = []
        
        self.graph[branch].extend(depends_on)
        for dep in depends_on:
            if dep not in self.reverse_graph:
                self.reverse_graph[dep] = []
            self.reverse_graph[dep].append(branch)
    
    def get_dependents(self, branch: str) -> List[str]:
        """
        Get branches that depend on the given branch.
        
        Args:
            branch: Name of the branch
            
        Returns:
            List of branch names that depend on this branch
        """
        return self.reverse_graph.get(branch, [])
    
    def get_all_dependents(self, branch: str) -> List[str]:
        """
        Get all branches that transitively depend on the given branch.
        
        Args:
            branch: Name of the branch
            
        Returns:
            List of all branch names that depend on this branch (direct and indirect)
        """
        dependents = []
        visited = set()
        
        def traverse(b: str):
            if b in visited:
                return
            visited.add(b)
            
            for dep in self.get_dependents(b):
                dependents.append(dep)
                traverse(dep)
        
        traverse(branch)
        return dependents


class GitFlow:
    """Git-Flow workflow orchestration with gate-based branching."""
    
    def __init__(self, repo_root: Optional[Path] = None, dry_run: bool = False):
        """
        Initialize the Git-Flow workflow manager.
        
        Args:
            repo_root: Path to the repository root (defaults to current directory)
            dry_run: If True, operations will not actually execute
        """
        self.repo_root = repo_root or Path.cwd()
        self.skill_dir = self.repo_root / '.iflow' / 'skills' / 'git-flow'
        self.config_file = self.skill_dir / 'config.json'
        self.phases_file = self.skill_dir / 'phases.json'
        self.workflow_state_file = self.skill_dir / 'workflow-state.json'
        self.branch_states_file = self.skill_dir / 'branch-states.json'
        self.git_manage_path = self.skill_dir / '..' / 'git-manage' / 'git-manage.py'
        self.dry_run = dry_run
        
        self.logger = StructuredLogger(
            name="git-flow",
            log_dir=self.repo_root / ".iflow" / "logs",
            log_level=LogLevel.INFO,
            log_format=LogFormat.JSON
        )
        self.checkpoint_manager = CheckpointManager(self.repo_root)
        self.prerequisite_checker = PrerequisiteChecker(self.repo_root)
        self.pipeline_update_manager = PipelineUpdateManager('git-flow', self.skill_dir)
        
        self.load_config()
        self.load_phases()
        self.workflow_state: Optional[WorkflowState] = None
        self.dependency_graph = DependencyGraph()
        self.load_workflow_state()
        self.load_branch_states()
    
    def load_config(self):
        """Load configuration from config.json file."""
        default_config = {
            "workflow": {
                "auto_detect_role": True,
                "auto_create_branch": True,
                "auto_phase_transition": True,
                "require_all_phases": False,
                "require_all_phases": False,
                "allow_parallel_phases": False,
                "phases_file": None
            },
            "merge": {
                "strategy": "rebase-merge",
                "delete_branch_after_merge": True,
                "require_dependencies_merged": True
            },
            "unapproval": {
                "allow_unapprove_after_merge": True,
                "default_action": "cascade-revert",
                "require_cascade_confirmation": True,
                "preserve_branch_after_revert": True,
                "auto_create_fix_branch": False
            },
            "notifications": {
                "enabled": True,
                "on_approve": True,
                "on_reject": True,
                "on_phase_change": True
            },
            "git_manage": {
                "command_path": ".iflow/skills/git-manage/git-manage.py"
            },
            "branch_protection": {
                "protected_branches": ["main", "master", "production"]
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    
                # Validate user config against schema if schema exists
                schema_dir = self.repo_root / '.iflow' / 'schemas'
                schema_file = schema_dir / 'git-flow-config.json'
                if schema_file.exists():
                    is_valid, errors = validate_json_schema(user_config, schema_file)
                    if not is_valid:
                        self.logger.warning(f"Config validation failed: {errors}. Using default config.")
                        self.config = default_config
                    else:
                        self.config = self._merge_config(default_config, user_config)
                else:
                    # No schema file, just merge configs
                    self.config = self._merge_config(default_config, user_config)
            except (json.JSONDecodeError, IOError):
                self.config = default_config
        else:
            self.config = default_config
    
    def _merge_config(self, default: Dict, user: Dict) -> Dict:
        """
        Recursively merge user config with default config.
        
        Args:
            default: Default configuration dictionary
            user: User configuration dictionary
            
        Returns:
            Merged configuration
        """
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def load_phases(self):
        """Load workflow phases from phases.json file."""
        default_phases = [
            {"name": "Requirements Gathering", "role": "Client", "order": 1, "required": True},
            {"name": "Architecture Design", "role": "Tech Lead", "order": 2, "required": True},
            {"name": "Implementation", "role": "Software Engineer", "order": 3, "required": True},
            {"name": "Testing", "role": "QA Engineer", "order": 4, "required": True},
            {"name": "Design", "role": "UI/UX Designer", "order": 5, "required": False},
            {"name": "Documentation", "role": "Documentation Specialist", "order": 6, "required": False},
            {"name": "Security Review", "role": "Security Engineer", "order": 7, "required": False},
            {"name": "Deployment", "role": "DevOps Engineer", "order": 8, "required": True}
        ]
        
        phases_file = self.config.get("workflow", {}).get("phases_file")
        if phases_file:
            phases_path = self.skill_dir / phases_file
            if phases_path.exists():
                with open(phases_path, 'r') as f:
                    phases_data = json.load(f)
                    self.phases = [Phase.from_dict(p) for p in phases_data.get("phases", default_phases)]
            else:
                self.phases = [Phase.from_dict(p) for p in default_phases]
        elif self.phases_file.exists():
            with open(self.phases_file, 'r') as f:
                phases_data = json.load(f)
                self.phases = [Phase.from_dict(p) for p in phases_data.get("phases", default_phases)]
        else:
            self.phases = [Phase.from_dict(p) for p in default_phases]
    
    def load_workflow_state(self):
        """
        Load workflow state with file locking and schema validation.
        
        Loads the workflow state from the state file, validates it against
        the schema, and initializes the workflow state object.
        """
        if self.workflow_state_file.exists():
            try:
                data = read_locked_json(self.workflow_state_file)
                
                # Validate against schema
                schema_dir = self.repo_root / '.iflow' / 'schemas'
                is_valid, errors = validate_workflow_state(data, schema_dir)
                
                if not is_valid:
                    self.logger.warning(f"Workflow state validation failed: {errors}")
                    # Continue loading despite validation errors for backward compatibility
                
                self.workflow_state = WorkflowState.from_dict(data)
            except (json.JSONDecodeError, IOError, FileLockError):
                self.workflow_state = None
    
    def load_branch_states(self):
        """
        Load branch states with file locking and schema validation.
        
        Loads all branch states from the branch states file, validates each
        against the schema, and populates the workflow state branches dictionary.
        """
        if self.workflow_state and self.branch_states_file.exists():
            try:
                data = read_locked_json(self.branch_states_file)
                
                # Validate against schema
                schema_dir = self.repo_root / '.iflow' / 'schemas'
                
                for branch_name, branch_data in data.items():
                    is_valid, errors = validate_branch_state(branch_data, schema_dir)
                    
                    if not is_valid:
                        self.logger.warning(f"Branch state validation failed for {branch_name}: {errors}")
                        # Continue loading despite validation errors for backward compatibility
                    
                    branch = BranchState.from_dict(branch_data)
                    self.workflow_state.branches[branch_name] = branch
            except (json.JSONDecodeError, IOError, FileLockError):
                pass
    
    def save_workflow_state(self):
        """
        Save workflow state with file locking.
        
        Serializes the current workflow state to JSON and writes it to
        the state file with file locking for thread safety.
        """
        if self.workflow_state:
            self.workflow_state.updated_at = datetime.now().isoformat()
            if self.dry_run:
                self.logger.info(f'[DRY-RUN] Would save workflow state to: {self.workflow_state_file}')
                return
            try:
                write_locked_json(self.workflow_state_file, self.workflow_state.to_dict())
            except FileLockError as e:
                self.logger.warning(f"Failed to save workflow state: {e}")
    
    def save_branch_states(self):
        """
        Save branch states with file locking.
        
        Serializes all branch states to JSON and writes them to
        the branch states file with file locking for thread safety.
        """
        if self.workflow_state:
            if self.dry_run:
                self.logger.info(f'[DRY-RUN] Would save branch states to: {self.branch_states_file}')
                return
            try:
                write_locked_json(
                    self.branch_states_file,
                    {k: v.to_dict() for k, v in self.workflow_state.branches.items()}
                )
            except FileLockError as e:
                self.logger.warning(f"Failed to save branch states: {e}")
    
    def run_git_command(self, command: List[str], timeout: Optional[int] = 120) -> Tuple[int, str, str]:
        """Run a git command with timeout handling."""
        if self.dry_run:
            return 0, f'[DRY-RUN] Would execute: git {" ".join(command)}', ''
        
        try:
            return run_git_command(command, cwd=self.repo_root, timeout=timeout)
        except GitCommandError as e:
            return e.returncode, '', e.message
        except GitCommandTimeout as e:
            return 124, '', str(e)
    
    def run_git_manage(self, args: List[str], timeout: Optional[int] = 120) -> Tuple[int, str, str]:
        """Run git-manage script with timeout handling."""
        git_manage_path = self.config.get("git_manage", {}).get("command_path", ".iflow/skills/git-manage/git-manage.py")
        git_manage_script = self.repo_root / git_manage_path
        
        if not git_manage_script.exists():
            return 1, '', f'git-manage not found at {git_manage_path}'
        
        try:
            result = subprocess.run(
                [sys.executable, str(git_manage_script)] + args,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, '', f'git-manage command timed out after {timeout} seconds'
        except Exception as e:
            return 1, '', str(e)
    
    def get_current_branch(self) -> str:
        """Get current branch name."""
        try:
            return get_current_branch(self.repo_root)
        except (GitError, IOError, OSError):
            return 'unknown'
    
    def is_protected_branch(self, branch: str) -> bool:
        protected = self.config.get("branch_protection", {}).get("protected_branches", ["main", "master"])
        return branch in protected
    
    def detect_role(self) -> str:
        current_branch = self.get_current_branch()
        
        if '/' in current_branch:
            role = current_branch.split('/')[0].replace('-', ' ').title()
            return role
        
        if self.workflow_state and self.workflow_state.current_phase > 0:
            phase = self.workflow_state.phases[self.workflow_state.current_phase - 1]
            return phase.role
        
        return 'Software Engineer'
    
    def to_slug(self, text: str) -> str:
        return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    
    def generate_branch_name(self, role: str, feature: str) -> str:
        role_slug = self.to_slug(role)
        feature_slug = self.to_slug(feature)
        short_id = datetime.now().strftime('%H%M%S')
        return f"{role_slug}/{feature_slug}-{short_id}"
    
    def create_branch(self, name: str) -> Tuple[int, str]:
        """Create a new branch with validation."""
        # Validate branch name
        is_valid, error_msg = validate_branch_name(name)
        if not is_valid:
            return 1, f'Invalid branch name: {error_msg}'
        
        code, stdout, stderr = self.run_git_command(['checkout', '-b', name])
        if code == 0:
            return 0, f'Created branch: {name}'
        else:
            return code, f'Failed to create branch: {stderr}'
    
    def start_workflow(self, feature: str, resume: bool = False) -> Tuple[int, str]:
        if self.workflow_state:
            if resume:
                # Resume workflow
                return self.resume_workflow()
            else:
                return 1, 'Workflow already exists. Use status to view current workflow.'
        
        self.workflow_state = WorkflowState(feature)
        self.workflow_state.phases = [p for p in self.phases]
        self.workflow_state.status = WorkflowStatus.IN_PROGRESS
        
        self.save_workflow_state()
        
        output = [
            f'✓ Workflow initialized',
            f'Feature: {feature}',
            f'Phases: {len(self.phases)}',
            '',
            f'To start Phase 1, use: /git-flow phase next'
        ]
        
        return 0, '\n'.join(output)
    
    def resume_workflow(self) -> Tuple[int, str]:
        """
        Resume a previously interrupted workflow.
        
        Returns:
            Tuple of (exit_code, output_message)
        """
        if not self.workflow_state:
            return 1, 'No workflow found. Use /git-flow start <feature> to begin a new workflow.'
        
        if self.workflow_state.status == WorkflowStatus.COMPLETE:
            return 0, 'Workflow is already complete.'
        
        # Re-validate the workflow state
        output = [
            f'✓ Workflow resumed',
            f'Feature: {self.workflow_state.feature}',
            f'Status: {self.workflow_state.status.value}',
            f'Current Phase: {self.workflow_state.current_phase}',
            '',
            'Phase Status:',
        ]
        
        # Check each phase and update status based on actual git state
        for phase in self.workflow_state.phases:
            status_icon = '⏸' if phase.status == PhaseStatus.PENDING else \
                          '▶' if phase.status == PhaseStatus.ACTIVE else \
                          '✓' if phase.status == PhaseStatus.COMPLETE else \
                          '🚫'
            required_icon = '*' if phase.required else ''
            
            output.append(f'  {status_icon} Phase {phase.order}: {phase.name} ({phase.role}){required_icon}')
            
            # If phase has a branch, verify it still exists
            if phase.branch:
                code, stdout, stderr = self.run_git_command(['branch', '--list', phase.branch])
                if not stdout.strip():
                    output.append(f'    ⚠ Warning: Branch {phase.branch} not found')
        
        # Find the next incomplete phase
        next_phase = None
        for phase in self.workflow_state.phases:
            if phase.status in [PhaseStatus.PENDING, PhaseStatus.ACTIVE]:
                # Check if dependencies are satisfied
                deps_satisfied = True
                for dep_order in phase.dependencies:
                    dep_phase = self.workflow_state.phases[dep_order - 1]
                    if dep_phase.status != PhaseStatus.COMPLETE:
                        deps_satisfied = False
                        break
                
                if deps_satisfied:
                    next_phase = phase
                    break
        
        output.append('')
        
        if next_phase:
            if next_phase.status == PhaseStatus.ACTIVE:
                output.append(f'Current active phase: Phase {next_phase.order} ({next_phase.name})')
                output.append(f'Use /git-flow status to view detailed information')
            else:
                output.append(f'Next phase ready: Phase {next_phase.order} ({next_phase.name})')
                output.append(f'Use /git-flow phase next to activate it')
        else:
            output.append('All phases are complete or blocked.')
        
        # Check for timeouts
        code, timeout_output = self.enforce_phase_timeouts()
        if code != 0:
            output.append('')
            output.append(timeout_output)
        
        self.save_workflow_state()
        
        return 0, '\n'.join(output)
    
    def commit(self, files: List[str]) -> Tuple[int, str]:
        if not self.workflow_state:
            return 1, 'No workflow initialized. Use /git-flow start <feature> to begin.'
        
        if self.workflow_state.current_phase == 0:
            return 1, 'No active phase. Use /git-flow phase next to activate the first phase.'
        
        role = self.detect_role()
        current_branch = self.get_current_branch()
        
        if self.is_protected_branch(current_branch):
            if self.config.get("workflow", {}).get("auto_create_branch", True):
                feature = self.workflow_state.feature
                new_branch = self.generate_branch_name(role, feature)
                code, output = self.create_branch(new_branch)
                if code != 0:
                    return code, output
                current_branch = new_branch
            else:
                return 1, f'Cannot commit to protected branch "{current_branch}". Create a feature branch first.'
        
        phase = self.workflow_state.phases[self.workflow_state.current_phase - 1]
        
        if current_branch not in self.workflow_state.branches:
            branch_state = BranchState(current_branch, role, phase.order)
            self.workflow_state.branches[current_branch] = branch_state
        
        code, stdout, stderr = self.run_git_manage(['commit'] + files)
        
        if code == 0:
            branch_state = self.workflow_state.branches[current_branch]
            if current_branch != phase.branch:
                phase.branch = current_branch
            
            output_lines = [
                f'✓ Commit successful',
                f'Branch: {current_branch}',
                f'Role: {role}',
                f'Phase: {phase.order} - {phase.name}',
                '',
                f'{stdout}'
            ]
            return 0, '\n'.join(output_lines)
        else:
            return code, f'Commit failed: {stderr}'
    
    def review(self) -> Tuple[int, str]:
        if not self.workflow_state:
            return 1, 'No workflow initialized.'
        
        pending_branches = [
            b for b in self.workflow_state.branches.values()
            if b.status in [BranchStatus.PENDING, BranchStatus.REVIEWING, BranchStatus.APPROVED]
        ]
        
        if not pending_branches:
            return 0, 'No branches pending review.'
        
        output = [
            '📋 Git-Flow Review Dashboard',
            f'Feature: {self.workflow_state.feature}',
            f'Status: {self.workflow_state.status.value.title()} (Phase {self.workflow_state.current_phase}/{len(self.workflow_state.phases)})',
            '',
            'Pending Reviews:'
        ]
        
        for i, branch in enumerate(pending_branches, 1):
            phase = self.workflow_state.phases[branch.phase - 1]
            status_icon = {
                BranchStatus.PENDING: '⏳',
                BranchStatus.REVIEWING: '👀',
                BranchStatus.APPROVED: '✅'
            }.get(branch.status, '❓')
            
            output.append('')
            output.append(f'[{i}] {branch.name}')
            output.append(f'    Role: {branch.role}')
            output.append(f'    Phase: {branch.order} - {phase.name}')
            output.append(f'    Commits: {len(branch.commits)}')
            output.append(f'    Status: {status_icon} {branch.status.value}')
            output.append(f'    Created: {branch.created_at}')
            
            if branch.commits:
                last_commit = branch.commits[-1]
                output.append(f'    Last commit: {last_commit.get("message", "N/A")}')
        
        output.append('')
        output.append('Actions:')
        output.append('[A] Approve: /git-flow review approve <branch>')
        output.append('[R] Reject: /git-flow review reject <branch> --reason "text"')
        output.append('[C] Request Changes: /git-flow review request-changes <branch> --comment "text"')
        
        return 0, '\n'.join(output)
    
    def review_approve(self, branch_name: str, comment: Optional[str] = None) -> Tuple[int, str]:
        if not self.workflow_state:
            return 1, 'No workflow initialized.'
        
        if branch_name not in self.workflow_state.branches:
            return 1, f'Branch "{branch_name}" not found in workflow.'
        
        branch = self.workflow_state.branches[branch_name]
        
        if branch.status == BranchStatus.MERGED:
            return 1, f'Branch "{branch_name}" is already merged.'
        
        branch.status = BranchStatus.APPROVED
        branch.approved_by = "you"
        branch.approved_at = datetime.now().isoformat()
        
        event = ReviewEvent("approve", "you", comment=comment)
        branch.review_history.append(event.to_dict())
        
        output = [
            f'✓ Approved: {branch_name}',
            ''
        ]
        
        if comment:
            output.append(f'💬 Comment: "{comment}"')
            output.append('')
        
        output.append('Starting merge...')
        
        code, merge_output = self.merge_branch(branch_name)
        
        if code == 0:
            output.append(merge_output)
            
            phase = self.workflow_state.phases[branch.phase - 1]
            if self.check_phase_complete(phase):
                output.append('')
                output.append(f'✓ Phase {phase.order} ({phase.name}) complete!')
                
                if self.config.get("workflow", {}).get("auto_phase_transition", True):
                    next_phase = self.get_next_phase(phase)
                    if next_phase:
                        output.append(self.advance_to_next_phase(phase)[1])
        else:
            output.append(f'❌ Merge failed: {merge_output}')
        
        self.save_branch_states()
        self.save_workflow_state()
        
        return 0, '\n'.join(output)
    
    def merge_branch(self, branch_name: str) -> Tuple[int, str]:
        if not self.workflow_state:
            return 1, 'No workflow initialized.'
        
        branch = self.workflow_state.branches[branch_name]
        
        if self.config.get("merge", {}).get("require_dependencies_merged", True):
            for dep_name in branch.dependencies:
                dep_branch = self.workflow_state.branches.get(dep_name)
                if dep_branch and dep_branch.status != BranchStatus.MERGED:
                    return 1, f'Dependency "{dep_name}" is not merged yet.'
        
        output = []
        
        output.append(f'Step 1: Checkout main...')
        code, stdout, stderr = self.run_git_command(['checkout', 'main'])
        if code != 0:
            return code, f'Failed to checkout main: {stderr}'
        output.append('✓ Checkout main')
        
        output.append(f'Step 2: Pull latest changes...')
        code, stdout, stderr = self.run_git_command(['pull'])
        if code != 0:
            return code, f'Failed to pull: {stderr}'
        output.append('✓ Pull complete')
        
        output.append(f'Step 3: Checkout {branch_name}...')
        code, stdout, stderr = self.run_git_command(['checkout', branch_name])
        if code != 0:
            return code, f'Failed to checkout {branch_name}: {stderr}'
        output.append(f'✓ Checkout {branch_name}')
        
        output.append(f'Step 4: Rebase onto main...')
        code, stdout, stderr = self.run_git_command(['rebase', 'main'])
        if code != 0:
            return code, f'Rebase failed: {stderr}'
        output.append('✓ Rebase complete')
        
        output.append(f'Step 5: Checkout main...')
        code, stdout, stderr = self.run_git_command(['checkout', 'main'])
        if code != 0:
            return code, f'Failed to checkout main: {stderr}'
        output.append('✓ Checkout main')
        
        output.append(f'Step 6: Merge {branch_name}...')
        code, stdout, stderr = self.run_git_command(['merge', '--no-ff', branch_name])
        if code != 0:
            return code, f'Merge failed: {stderr}'
        output.append('✓ Merge complete')
        
        code, stdout, stderr = self.run_git_command(['log', '-1', '--pretty=%H'])
        if code == 0:
            merge_commit = stdout.strip()
            branch.merge_commit = merge_commit
            branch.status = BranchStatus.MERGED
            
            event = ReviewEvent("merge", "you", merge_commit=merge_commit)
            branch.review_history.append(event.to_dict())
        
        if self.config.get("merge", {}).get("delete_branch_after_merge", True):
            output.append(f'Step 7: Delete branch {branch_name}...')
            self.run_git_command(['branch', '-D', branch_name])
            output.append('✓ Branch deleted')
        
        return 0, '\n'.join(output)
    
    def check_for_conflicts(self) -> Tuple[bool, List[str]]:
        """
        Check if there are any git merge conflicts.
        
        Returns:
            Tuple of (has_conflicts, list_of_conflicted_files)
        """
        code, stdout, stderr = self.run_git_command(['diff', '--name-only', '--diff-filter=U'])
        
        if code != 0:
            return False, []
        
        if not stdout.strip():
            return False, []
        
        conflicted_files = [line.strip() for line in stdout.strip().split('\n') if line.strip()]
        
        return bool(conflicted_files), conflicted_files
    
    def check_phase_timeout(self, phase: Phase) -> Tuple[bool, Optional[str]]:
        """
        Check if a phase has exceeded its timeout.
        
        Args:
            phase: The phase to check
            
        Returns:
            Tuple of (is_timeout, warning_message)
        """
        if phase.status != PhaseStatus.ACTIVE:
            return False, None
        
        if not phase.started_at:
            return False, None
        
        try:
            from datetime import datetime, timezone
            import time
            
            started = datetime.fromisoformat(phase.started_at)
            now = datetime.now(timezone.utc)
            
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            
            elapsed_seconds = (now - started).total_seconds()
            
            # Check if we're past the timeout
            if elapsed_seconds > phase.timeout_seconds:
                return True, f"Phase {phase.order} ({phase.name}) has exceeded its timeout of {phase.timeout_seconds} seconds"
            
            # Check if we should send a warning (80% of timeout)
            if not phase.timeout_warning_sent and elapsed_seconds > (phase.timeout_seconds * 0.8):
                phase.timeout_warning_sent = True
                return False, f"Phase {phase.order} ({phase.name}) is approaching its timeout of {phase.timeout_seconds} seconds"
            
            return False, None
            
        except (ValueError, TypeError) as e:
            return False, None
    
    def enforce_phase_timeouts(self) -> Tuple[int, str]:
        """
        Check all active phases for timeout violations.
        
        Returns:
            Tuple of (exit_code, output_message)
        """
        if not self.workflow_state:
            return 0, 'No workflow initialized.'
        
        warnings = []
        timeouts = []
        
        for phase in self.workflow_state.phases:
            is_timeout, message = self.check_phase_timeout(phase)
            
            if is_timeout:
                timeouts.append(message)
            elif message:
                warnings.append(message)
        
        output = []
        
        if timeouts:
            output.append('⚠ Phase Timeout Warnings:')
            for timeout_msg in timeouts:
                output.append(f'  - {timeout_msg}')
            output.append('')
            output.append('Recommendation: Review phase progress and consider extending timeout or marking as complete.')
        
        if warnings:
            if timeouts:
                output.append('')
            output.append('⏰ Phase Timeout Warnings:')
            for warning_msg in warnings:
                output.append(f'  - {warning_msg}')
        
        if not output:
            return 0, 'All active phases are within their timeout limits.'
        
        return 1, '\n'.join(output)
    
    def abort_merge_operation(self) -> Tuple[int, str]:
        """
        Abort the current merge/rebase operation and clean up.
        
        Returns:
            Tuple of (exit_code, output_message)
        """
        output = ['Aborting merge/rebase operation...']
        
        # Try to abort rebase first
        code, stdout, stderr = self.run_git_command(['rebase', '--abort'])
        if code == 0:
            output.append('✓ Rebase aborted')
        else:
            # Try to abort merge
            code, stdout, stderr = self.run_git_command(['merge', '--abort'])
            if code == 0:
                output.append('✓ Merge aborted')
            else:
                output.append('⚠ No merge/rebase in progress')
        
        # Clean up any conflict markers
        code, stdout, stderr = self.run_git_command(['reset', '--hard', 'HEAD'])
        if code == 0:
            output.append('✓ Working directory cleaned')
        
        return 0, '\n'.join(output)
    
    def resolve_conflicts_with_strategy(self, strategy: str = 'theirs') -> Tuple[int, str]:
        """
        Automatically resolve conflicts using a strategy.
        
        Args:
            strategy: Conflict resolution strategy ('ours', 'theirs', 'manual')
        
        Returns:
            Tuple of (exit_code, output_message)
        """
        has_conflicts, conflicted_files = self.check_for_conflicts()
        
        if not has_conflicts:
            return 0, 'No conflicts to resolve'
        
        output = [
            f'Resolving conflicts using strategy: {strategy}',
            f'Conflicted files: {len(conflicted_files)}',
            ''
        ]
        
        if strategy == 'ours':
            # Accept our changes for all conflicts
            code, stdout, stderr = self.run_git_command(['checkout', '--ours', '.'])
            if code == 0:
                output.append('✓ Accepted our changes for all files')
            else:
                return code, f'Failed to apply "ours" strategy: {stderr}'
        
        elif strategy == 'theirs':
            # Accept their changes for all conflicts
            code, stdout, stderr = self.run_git_command(['checkout', '--theirs', '.'])
            if code == 0:
                output.append('✓ Accepted their changes for all files')
            else:
                return code, f'Failed to apply "theirs" strategy: {stderr}'
        
        elif strategy == 'manual':
            # Cannot automatically resolve
            output.append('Manual resolution required.')
            output.append('')
            output.append('Conflicted files:')
            for file_path in conflicted_files:
                output.append(f'  - {file_path}')
            output.append('')
            output.append('To resolve manually:')
            output.append('1. Edit conflicted files and resolve markers (<<<<<, ======, >>>>>)')
            output.append('2. git add <resolved-files>')
            output.append('3. git commit (for merge) or git rebase --continue (for rebase)')
            return 1, '\n'.join(output)
        
        else:
            return 1, f'Unknown conflict resolution strategy: {strategy}'
        
        # Stage resolved files
        code, stdout, stderr = self.run_git_command(['add', '.'])
        if code != 0:
            return code, f'Failed to stage resolved files: {stderr}'
        
        output.append('✓ Resolved files staged')
        
        return 0, '\n'.join(output)
    
    def merge_branch(self, branch_name: str) -> Tuple[int, str]:
        """
        Merge a branch with automatic conflict detection and handling.
        
        Args:
            branch_name: Name of branch to merge
        
        Returns:
            Tuple of (exit_code, output_message)
        """
        if not self.workflow_state:
            return 1, 'No workflow initialized.'
        
        branch = self.workflow_state.branches[branch_name]
        
        # Validate dependencies before merge
        if self.config.get("merge", {}).get("require_dependencies_merged", True):
            validation_result = self._validate_dependencies_for_merge(branch_name)
            if not validation_result[0]:
                return 1, validation_result[1]
        
        output = []
        
        output.append(f'Step 1: Checkout main...')
        code, stdout, stderr = self.run_git_command(['checkout', 'main'])
        if code != 0:
            return code, f'Failed to checkout main: {stderr}'
        output.append('✓ Checkout main')
        
        output.append(f'Step 2: Pull latest changes...')
        code, stdout, stderr = self.run_git_command(['pull'])
        if code != 0:
            return code, f'Failed to pull: {stderr}'
        output.append('✓ Pull complete')
        
        output.append(f'Step 3: Checkout {branch_name}...')
        code, stdout, stderr = self.run_git_command(['checkout', branch_name])
        if code != 0:
            return code, f'Failed to checkout {branch_name}: {stderr}'
        output.append(f'✓ Checkout {branch_name}')
        
        output.append(f'Step 4: Rebase onto main...')
        code, stdout, stderr = self.run_git_command(['rebase', 'main'])
        
        if code != 0:
            # Check for conflicts
            has_conflicts, conflicted_files = self.check_for_conflicts()
            
            if has_conflicts:
                output.append('⚠ Rebase conflicts detected!')
                output.append('')
                output.append(f'Conflicted files ({len(conflicted_files)}):')
                for file_path in conflicted_files:
                    output.append(f'  - {file_path}')
                output.append('')
                output.append('Conflict resolution options:')
                output.append('[A] Abort and retry later: /git-flow resolve abort')
                output.append('[O] Accept our changes: /git-flow resolve ours')
                output.append('[T] Accept their changes: /git-flow resolve theirs')
                output.append('[M] Manual resolution: /git-flow resolve manual')
                
                # Mark branch as conflicted
                branch.status = BranchStatus.REJECTED
                event = ReviewEvent("conflict", "system", reason="Rebase conflict detected")
                branch.review_history.append(event.to_dict())
                
                self.save_branch_states()
                
                return 1, '\n'.join(output)
            else:
                return code, f'Rebase failed: {stderr}'
        
        output.append('✓ Rebase complete')
        
        output.append(f'Step 5: Checkout main...')
        code, stdout, stderr = self.run_git_command(['checkout', 'main'])
        if code != 0:
            return code, f'Failed to checkout main: {stderr}'
        output.append('✓ Checkout main')
        
        output.append(f'Step 6: Merge {branch_name}...')
        code, stdout, stderr = self.run_git_command(['merge', '--no-ff', branch_name])
        
        if code != 0:
            # Check for conflicts
            has_conflicts, conflicted_files = self.check_for_conflicts()
            
            if has_conflicts:
                output.append('⚠ Merge conflicts detected!')
                output.append('')
                output.append(f'Conflicted files ({len(conflicted_files)}):')
                for file_path in conflicted_files:
                    output.append(f'  - {file_path}')
                output.append('')
                output.append('Conflict resolution options:')
                output.append('[A] Abort and retry later: /git-flow resolve abort')
                output.append('[O] Accept our changes: /git-flow resolve ours')
                output.append('[T] Accept their changes: /git-flow resolve theirs')
                output.append('[M] Manual resolution: /git-flow resolve manual')
                
                # Mark branch as conflicted
                branch.status = BranchStatus.REJECTED
                event = ReviewEvent("conflict", "system", reason="Merge conflict detected")
                branch.review_history.append(event.to_dict())
                
                self.save_branch_states()
                
                return 1, '\n'.join(output)
            else:
                return code, f'Merge failed: {stderr}'
        
        output.append('✓ Merge complete')
        
        code, stdout, stderr = self.run_git_command(['log', '-1', '--pretty=%H'])
        if code == 0:
            merge_commit = stdout.strip()
            branch.merge_commit = merge_commit
            branch.status = BranchStatus.MERGED
            
            event = ReviewEvent("merge", "you", merge_commit=merge_commit)
            branch.review_history.append(event.to_dict())
        
        if self.config.get("merge", {}).get("delete_branch_after_merge", True):
            output.append(f'Step 7: Delete branch {branch_name}...')
            self.run_git_command(['branch', '-D', branch_name])
            output.append('✓ Branch deleted')
        
        return 0, '\n'.join(output)
    
    def _validate_dependencies_for_merge(self, branch_name: str) -> Tuple[bool, str]:
        """
        Validate that all dependencies are satisfied before merging.
        
        Args:
            branch_name: Name of branch to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if branch_name not in self.workflow_state.branches:
            return False, f'Branch "{branch_name}" not found in workflow'
        
        branch = self.workflow_state.branches[branch_name]
        
        # Check if branch has dependencies
        if not branch.dependencies:
            return True, ''
        
        # Validate each dependency
        for dep_name in branch.dependencies:
            if dep_name not in self.workflow_state.branches:
                return False, f'Dependency "{dep_name}" not found in workflow'
            
            dep_branch = self.workflow_state.branches[dep_name]
            
            # Check if dependency is merged
            if dep_branch.status != BranchStatus.MERGED:
                return False, (
                    f'Dependency "{dep_name}" is not merged yet. '
                    f'Current status: {dep_branch.status.value}. '
                    f'Please merge the dependency branch first.'
                )
            
            # Check if dependency merge commit exists
            if not dep_branch.merge_commit:
                return False, f'Dependency "{dep_name}" has no merge commit recorded'
            
            # Verify dependency is in the current branch history
            code, stdout, stderr = self.run_git_command(['merge-base', '--is-ancestor', dep_branch.merge_commit, 'HEAD'])
            if code != 0:
                return False, f'Dependency "{dep_name}" is not an ancestor of the current branch'
        
        # Check for circular dependencies using deadlock detector
        branch_states = {
            name: branch.to_dict()
            for name, branch in self.workflow_state.branches.items()
        }
        is_valid, deadlocks = validate_git_flow_dependencies(branch_states)
        
        if not is_valid:
            deadlock_msgs = [dl.description for dl in deadlocks]
            return False, f'Circular dependencies detected: {"; ".join(deadlock_msgs)}'
        
        return True, ''
    
    def _has_circular_dependency(self, branch_name: str, visited: Optional[set] = None) -> bool:
        """
        Check if a branch has circular dependencies using deadlock detector.
        
        Args:
            branch_name: Name of branch to check
            visited: Set of already visited branches (for recursion)
        
        Returns:
            True if circular dependency exists, False otherwise
        """
        if not self.workflow_state:
            return False
        
        # Use deadlock detector for comprehensive check
        branch_states = {
            name: branch.to_dict()
            for name, branch in self.workflow_state.branches.items()
        }
        is_valid, deadlocks = validate_git_flow_dependencies(branch_states)
        
        # Check if any deadlock involves the requested branch
        for deadlock in deadlocks:
            if branch_name in deadlock.cycle:
                return True
        
        return False
    
    def detect_deadlocks(self) -> Tuple[bool, List[Dict]]:
        """
        Detect all deadlocks in the current workflow.
        
        Returns:
            Tuple of (is_valid, list_of_deadlock_dicts)
        """
        if not self.workflow_state:
            return True, []
        
        branch_states = {
            name: branch.to_dict()
            for name, branch in self.workflow_state.branches.items()
        }
        is_valid, deadlocks = validate_git_flow_dependencies(branch_states)
        
        return is_valid, [dl.to_dict() for dl in deadlocks]
    
    def get_dependency_report(self) -> Dict:
        """
        Generate a comprehensive dependency report.
        
        Returns:
            Dictionary with dependency graph information
        """
        if not self.workflow_state:
            return {"total_nodes": 0, "total_dependencies": 0, "nodes": {}}
        
        detector = DeadlockDetector()
        
        # Build dependency graph
        for branch_name, branch in self.workflow_state.branches.items():
            for dep in branch.dependencies:
                detector.add_dependency(branch_name, dep)
        
        return detector.get_dependency_report()
    
    def create_checkpoint(
        self,
        name: str,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a workflow checkpoint.
        
        Args:
            name: Human-readable name for the checkpoint
            tags: Optional tags for categorization
            description: Optional description
            
        Returns:
            Dictionary with checkpoint information
        """
        if not self.workflow_state:
            raise IFlowError(
                "No workflow state to checkpoint",
                ErrorCode.INVALID_STATE
            )
        
        # Capture current state
        state_data = {
            "workflow_state": self.workflow_state.to_dict(),
            "current_branch": get_current_branch(self.repo_root),
            "timestamp": datetime.now().isoformat()
        }
        
        # Create metadata
        metadata = {
            "description": description,
            "workflow_status": self.workflow_state.status.value,
            "current_phase": self.workflow_state.current_phase
        }
        
        # Create checkpoint
        checkpoint = self.checkpoint_manager.create_checkpoint(
            name=name,
            state_data=state_data,
            metadata=metadata,
            tags=tags
        )
        
        self.logger.info(
            f"Created checkpoint: {checkpoint.checkpoint_id}",
            checkpoint_id=checkpoint.checkpoint_id,
            name=checkpoint.name
        )
        
        return checkpoint.to_dict()
    
    def restore_checkpoint(
        self,
        checkpoint_id: str,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Restore workflow state from a checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to restore
            validate: Whether to validate the restored state
            
        Returns:
            Restored state data
        """
        # Restore from checkpoint
        state_data = self.checkpoint_manager.restore_checkpoint(
            checkpoint_id=checkpoint_id,
            validate=validate
        )
        
        # Restore workflow state
        if "workflow_state" in state_data:
            self.workflow_state = WorkflowState.from_dict(state_data["workflow_state"])
            self.branch_states = self.workflow_state.branches
            
            # Save restored state
            self.save_workflow_state()
            self.save_branch_states()
        
        self.logger.info(
            f"Restored checkpoint: {checkpoint_id}",
            checkpoint_id=checkpoint_id
        )
        
        return state_data
    
    def list_checkpoints(
        self,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List workflow checkpoints.
        
        Args:
            status: Optional status filter
            tags: Optional tag filter
            limit: Optional maximum number to return
            
        Returns:
            List of checkpoint dictionaries
        """
        from checkpoint_manager import CheckpointStatus
        
        status_enum = CheckpointStatus(status) if status else None
        checkpoints = self.checkpoint_manager.list_checkpoints(
            status=status_enum,
            tags=tags,
            limit=limit
        )
        
        return [cp.to_dict() for cp in checkpoints]
    
    def delete_checkpoint(self, checkpoint_id: str):
        """
        Delete a workflow checkpoint.
        
        Args:
            checkpoint_id: ID of checkpoint to delete
        """
        self.checkpoint_manager.delete_checkpoint(checkpoint_id)
        self.logger.info(
            f"Deleted checkpoint: {checkpoint_id}",
            checkpoint_id=checkpoint_id
        )
    
    def get_checkpoint_statistics(self) -> Dict[str, Any]:
        """
        Get checkpoint statistics.
        
        Returns:
            Dictionary with statistics
        """
        return self.checkpoint_manager.get_statistics()
    
    def cleanup_failed_branches(
        self,
        max_age_days: int = 30,
        dry_run: bool = False
    ) -> Tuple[int, List[str]]:
        """
        Clean up branches that have failed or been abandoned.
        
        Args:
            max_age_days: Maximum age in days before cleanup
            dry_run: If True, only list branches without deleting
            
        Returns:
            Tuple of (count_deleted, list_of_branch_names)
        """
        if not self.workflow_state:
            return 0, []
        
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        deleted_branches = []
        
        for branch_name, branch in list(self.workflow_state.branches.items()):
            # Check if branch is in a failed or abandoned state
            if branch.status in [BranchStatus.NEEDS_CHANGES, BranchStatus.REJECTED]:
                # Check branch age
                branch_date = datetime.fromisoformat(branch.created_at)
                
                if branch_date < cutoff_date:
                    if not dry_run:
                        # Delete the branch
                        try:
                            code, stdout, stderr = self.run_git_command(
                                ['branch', '-D', branch_name]
                            )
                            
                            if code == 0:
                                # Remove from workflow state
                                del self.workflow_state.branches[branch_name]
                                deleted_branches.append(branch_name)
                                
                                self.logger.info(
                                    f"Cleaned up failed branch: {branch_name}",
                                    branch_name=branch_name,
                                    age_days=(datetime.now() - branch_date).days
                                )
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to cleanup branch {branch_name}: {str(e)}",
                                branch_name=branch_name,
                                error=str(e)
                            )
                    else:
                        deleted_branches.append(branch_name)
        
        if deleted_branches:
            self.save_branch_states()
            self.save_workflow_state()
        
        return len(deleted_branches), deleted_branches
    
    def delete_branch(
        self,
        branch_name: str,
        force: bool = False
    ) -> Tuple[int, str]:
        """
        Delete a branch.
        
        Args:
            branch_name: Name of branch to delete
            force: Whether to force delete (use -D instead of -d)
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        # Check if branch is protected
        protected_branches = self.config.get("branch_protection", {}).get(
            "protected_branches", ["main", "master", "production"]
        )
        
        if branch_name in protected_branches:
            return 1, f"Cannot delete protected branch: {branch_name}"
        
        # Delete the branch
        flag = "-D" if force else "-d"
        code, stdout, stderr = self.run_git_command(['branch', flag, branch_name])
        
        if code != 0:
            return code, f"Failed to delete branch: {stderr}"
        
        # Remove from workflow state if present
        if self.workflow_state and branch_name in self.workflow_state.branches:
            del self.workflow_state.branches[branch_name]
            self.save_branch_states()
            self.save_workflow_state()
        
        message = f"Deleted branch: {branch_name}"
        self.logger.info(message, branch_name=branch_name, force=force)
        
        return 0, message
    
    def cleanup_orphaned_branches(self, dry_run: bool = False) -> Tuple[int, List[str]]:
        """
        Clean up branches that exist in git but not in workflow state.
        
        Args:
            dry_run: If True, only list branches without deleting
            
        Returns:
            Tuple of (count_deleted, list_of_branch_names)
        """
        # Get all branches from git
        code, stdout, stderr = self.run_git_command(['branch', '--format=%(refname:short)'])
        
        if code != 0:
            return 0, []
        
        git_branches = [b.strip() for b in stdout.split('\n') if b.strip()]
        protected_branches = self.config.get("branch_protection", {}).get(
            "protected_branches", ["main", "master", "production"]
        )
        
        orphaned_branches = []
        
        if self.workflow_state:
            workflow_branches = set(self.workflow_state.branches.keys())
            
            for branch_name in git_branches:
                # Skip protected branches
                if branch_name in protected_branches:
                    continue
                
                # Check if branch is not in workflow state
                if branch_name not in workflow_branches:
                    orphaned_branches.append(branch_name)
                    
                    if not dry_run:
                        code, stdout, stderr = self.run_git_command(['branch', '-D', branch_name])
                        
                        if code == 0:
                            self.logger.info(
                                f"Cleaned up orphaned branch: {branch_name}",
                                branch_name=branch_name
                            )
        
        return len(orphaned_branches), orphaned_branches
    
    def check_prerequisites(
        self,
        required_tools: Optional[List[str]] = None,
        required_env_vars: Optional[List[str]] = None,
        min_disk_space_mb: int = 100
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check workflow prerequisites before execution.
        
        Args:
            required_tools: List of required tools (default: ['git'])
            required_env_vars: List of required environment variables
            min_disk_space_mb: Minimum required disk space in MB
            
        Returns:
            Tuple of (all_passed, result_dict)
        """
        if required_tools is None:
            required_tools = ['git']
        
        return validate_workflow_prerequisites(
            repo_root=self.repo_root,
            required_tools=required_tools,
            required_env_vars=required_env_vars,
            min_disk_space_mb=min_disk_space_mb
        )
    
    def validate_before_operation(self, operation: str) -> Tuple[bool, str]:
        """
        Validate prerequisites before performing an operation.
        
        Args:
            operation: Name of the operation to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check git repository
        git_check = self.prerequisite_checker.check_git_repository()
        if git_check.status.name != "PASSED":
            return False, git_check.message or "Not a git repository"
        
        # Check disk space
        space_check = self.prerequisite_checker.check_disk_space(min_space_mb=100)
        if space_check.status.name == "FAILED":
            return False, space_check.message or "Insufficient disk space"
        
        # Check for workflow state file permissions if operating on state
        if operation in ["init", "start", "next", "complete", "approve"]:
            perm_check = self.prerequisite_checker.check_permissions(
                self.workflow_state_file,
                "write"
            )
            if perm_check.status.name == "FAILED":
                return False, perm_check.message or "Cannot write workflow state file"
        
        # Check for branch state file permissions
        if operation in ["create_branch", "merge_branch"]:
            perm_check = self.prerequisite_checker.check_permissions(
                self.branch_states_file,
                "write"
            )
            if perm_check.status.name == "FAILED":
                return False, perm_check.message or "Cannot write branch states file"
        
        return True, ""
    
    def resolve_conflicts(self, strategy: str = 'manual') -> Tuple[int, str]:
        """
        Resolve merge/rebase conflicts using the specified strategy.
        
        Args:
            strategy: Conflict resolution strategy ('abort', 'ours', 'theirs', 'manual')
        
        Returns:
            Tuple of (exit_code, output_message)
        """
        has_conflicts, conflicted_files = self.check_for_conflicts()
        
        if not has_conflicts:
            return 0, 'No conflicts to resolve'
        
        if strategy == 'abort':
            return self.abort_merge_operation()
        
        # Resolve conflicts
        code, output = self.resolve_conflicts_with_strategy(strategy)
        
        if code != 0:
            return code, output
        
        # Continue the operation (merge or rebase)
        # Check if we're in a rebase
        code, stdout, stderr = self.run_git_command(['status', '--porcelain'])
        if code == 0 and 'rebase' in stdout:
            output.append('')
            output.append('Continuing rebase...')
            code, stdout, stderr = self.run_git_command(['rebase', '--continue'])
            if code != 0:
                return code, f'Failed to continue rebase: {stderr}'
            output.append('✓ Rebase continued successfully')
        else:
            # For merge, we need to create a commit
            output.append('')
            output.append('Completing merge commit...')
            code, stdout, stderr = self.run_git_command(['commit', '--no-edit'])
            if code != 0:
                return code, f'Failed to complete merge: {stderr}'
            output.append('✓ Merge completed successfully')
        
        # Get current branch and update its status
        current_branch = self.get_current_branch()
        if current_branch in self.workflow_state.branches:
            branch = self.workflow_state.branches[current_branch]
            branch.status = BranchStatus.PENDING
            event = ReviewEvent("resolved", "you", comment=f"Conflicts resolved using {strategy} strategy")
            branch.review_history.append(event.to_dict())
            self.save_branch_states()
        
        return 0, '\n'.join(output)
    
    def review_reject(self, branch_name: str, reason: str, keep_branch: bool = True) -> Tuple[int, str]:
        if not self.workflow_state:
            return 1, 'No workflow initialized.'
        
        if branch_name not in self.workflow_state.branches:
            return 1, f'Branch "{branch_name}" not found in workflow.'
        
        branch = self.workflow_state.branches[branch_name]
        branch.status = BranchStatus.REJECTED
        
        event = ReviewEvent("reject", "you", reason=reason)
        branch.review_history.append(event.to_dict())
        
        output = [
            f'✓ Rejected: {branch_name}',
            f'❌ Reason: "{reason}"',
            ''
        ]
        
        if keep_branch:
            output.append('⚠ Branch kept for fixes')
        else:
            output.append('🗑 Branch deleted')
            self.run_git_command(['branch', '-D', branch_name])
        
        output.append('')
        output.append('To fix:')
        output.append(f'1. git checkout {branch_name}')
        output.append('2. Make changes')
        output.append('3. /git-flow commit <files>')
        output.append('4. Resubmit for review')
        
        self.save_branch_states()
        
        return 0, '\n'.join(output)
    
    def review_request_changes(self, branch_name: str, comment: str) -> Tuple[int, str]:
        if not self.workflow_state:
            return 1, 'No workflow initialized.'
        
        if branch_name not in self.workflow_state.branches:
            return 1, f'Branch "{branch_name}" not found in workflow.'
        
        branch = self.workflow_state.branches[branch_name]
        branch.status = BranchStatus.NEEDS_CHANGES
        
        event = ReviewEvent("request_changes", "you", comment=comment)
        branch.review_history.append(event.to_dict())
        
        output = [
            f'✓ Changes requested: {branch_name}',
            f'💬 Comment: "{comment}"',
            '',
            f'To fix:']
        output.append(f'1. git checkout {branch_name}')
        output.append('2. Make changes')
        output.append('3. /git-flow commit <files>')
        output.append('4. Resubmit for review')
        
        self.save_branch_states()
        
        return 0, '\n'.join(output)
    
    def unapprove(self, branch_name: str, cascade: bool = False) -> Tuple[int, str]:
        if not self.workflow_state:
            return 1, 'No workflow initialized.'
        
        if branch_name not in self.workflow_state.branches:
            return 1, f'Branch "{branch_name}" not found in workflow.'
        
        branch = self.workflow_state.branches[branch_name]
        
        if branch.status != BranchStatus.MERGED:
            return 1, f'Branch "{branch_name}" is not merged. Use review reject instead.'
        
        if not self.config.get("unapproval", {}).get("allow_unapprove_after_merge", True):
            return 1, 'Unapproval after merge is disabled in configuration.'
        
        output = [
            f'⚠ Unapproving: {branch_name}',
            ''
        ]
        
        if cascade:
            dependents = self.dependency_graph.get_all_dependents(branch_name)
            to_revert = [branch_name] + dependents
            to_revert.sort(key=lambda b: self.workflow_state.branches[b].approved_at or '', reverse=True)
            
            output.append(f'Found {len(to_revert)} branches to revert:')
            for b in to_revert:
                output.append(f'  - {b}')
            output.append('')
            
            for b in to_revert:
                revert_output = self.revert_branch(b)
                output.append(revert_output)
        else:
            revert_output = self.revert_branch(branch_name)
            output.append(revert_output)
        
        output.append('')
        output.append('Next steps:')
        output.append('1. Fix issues in the branch')
        output.append('2. /git-flow commit <files>')
        output.append('3. Resubmit for review')
        
        self.save_branch_states()
        self.save_workflow_state()
        
        return 0, '\n'.join(output)
    
    def revert_branch(self, branch_name: str) -> str:
        if not self.workflow_state:
            return 'No workflow initialized.'
        
        branch = self.workflow_state.branches[branch_name]
        
        output = [
            f'Reverting: {branch_name}',
            ''
        ]
        
        if branch.merge_commit:
            code, stdout, stderr = self.run_git_command(['checkout', 'main'])
            if code != 0:
                return f'Failed to checkout main: {stderr}'
            
            revert_msg = f'Revert "Merge {branch_name}"\n\n' \
                        f"Original approval: {branch.approved_at}\n" \
                        f"Approver: {branch.approved_by}\n" \
                        f"Unapproved at: {datetime.now().isoformat()}"
            
            code, stdout, stderr = self.run_git_command(['revert', '-m', '1', branch.merge_commit, '-m', revert_msg])
            if code != 0:
                return f'Revert failed: {stderr}'
            
            branch.status = BranchStatus.UNAPPROVED
            branch.unapproved_by = "you"
            branch.unapproved_at = datetime.now().isoformat()
            
            event = ReviewEvent("unapprove", "you")
            branch.review_history.append(event.to_dict())
            
            output.append(f'✓ Reverted {branch_name}')
        else:
            output.append(f'⚠ No merge commit found for {branch_name}')
        
        return '\n'.join(output)
    
    def status(self) -> Tuple[int, str]:
        if not self.workflow_state:
            return 1, 'No workflow initialized. Use /git-flow start <feature> to begin.'
        
        output = [
            '📊 Git-Flow Status',
            f'Feature: {self.workflow_state.feature}',
            f'Status: {self.workflow_state.status.value.title()}',
            f'Created: {self.workflow_state.created_at}',
            ''
        ]
        
        output.append(f'Current Phase: {self.workflow_state.current_phase}/{len(self.workflow_state.phases)}')
        output.append('')
        
        for phase in self.workflow_state.phases:
            status_icon = {
                PhaseStatus.PENDING: '⏸',
                PhaseStatus.ACTIVE: '▶️',
                PhaseStatus.COMPLETE: '✅',
                PhaseStatus.BLOCKED: '🚫'
            }.get(phase.status, '❓')
            
            output.append(f'Phase {phase.order}: {phase.name} ({phase.role})')
            output.append(f'  Status: {status_icon} {phase.status.value}')
            
            if phase.branch:
                branch = self.workflow_state.branches.get(phase.branch)
                if branch:
                    output.append(f'  Branch: {phase.branch} ({branch.status.value})')
            
            output.append('')
        
        pending_branches = [
            b for b in self.workflow_state.branches.values()
            if b.status in [BranchStatus.PENDING, BranchStatus.REVIEWING, BranchStatus.APPROVED]
        ]
        
        if pending_branches:
            output.append('Pending Reviews:')
            for branch in pending_branches:
                output.append(f'  - {branch.name} ({branch.status.value})')
            output.append('')
        
        complete_phases = sum(1 for p in self.workflow_state.phases if p.status == PhaseStatus.COMPLETE)
        progress = int((complete_phases / len(self.workflow_state.phases)) * 100)
        output.append(f'Overall Progress: {progress}% ({complete_phases}/{len(self.workflow_state.phases)} phases complete)')
        
        return 0, '\n'.join(output)
    
    def get_next_phase(self, current_phase: Phase) -> Optional[Phase]:
        for phase in self.workflow_state.phases:
            if phase.order == current_phase.order + 1:
                return phase
        return None
    
    def check_phase_complete(self, phase: Phase) -> bool:
        """
        Check if a phase is complete.
        
        Args:
            phase: The phase to check
            
        Returns:
            True if complete, False otherwise
        """
        if phase.status != PhaseStatus.ACTIVE:
            return False
        
        # Optional phases can be skipped if configured
        if not phase.required and self.config.get("workflow", {}).get("allow_skip_optional_phases", False):
            return True  # Optional phases can auto-complete if skipping is allowed
        
        if not phase.branch:
            return False
        
        branch = self.workflow_state.branches.get(phase.branch)
        if not branch or branch.status != BranchStatus.MERGED:
            return False
        
        phase.status = PhaseStatus.COMPLETE
        phase.completed_at = datetime.now().isoformat()
        
        return True
    
    def skip_phase(self, phase_order: int, reason: Optional[str] = None) -> Tuple[int, str]:
        """
        Skip an optional phase.
        
        Args:
            phase_order: The phase number to skip
            reason: Reason for skipping
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        if not self.workflow_state:
            return 1, 'No workflow initialized.'
        
        if phase_order < 1 or phase_order > len(self.workflow_state.phases):
            return 1, f'Invalid phase number: {phase_order}'
        
        phase = self.workflow_state.phases[phase_order - 1]
        
        if phase.required:
            return 1, f'Phase {phase_order} ({phase.name}) is required and cannot be skipped.'
        
        if phase.status == PhaseStatus.COMPLETE:
            return 0, f'Phase {phase_order} ({phase.name}) is already complete.'
        
        if phase.status == PhaseStatus.ACTIVE:
            return 1, f'Phase {phase.order} ({phase.name}) is currently active and cannot be skipped.'
        
        phase.status = PhaseStatus.BLOCKED
        phase.completed_at = datetime.now().isoformat()
        
        # Add skip event to review history
        if phase.branch:
            branch = self.workflow_state.branches.get(phase.branch)
            if branch:
                branch.review_history.append({
                    "action": "skip",
                    "actor": "system",
                    "timestamp": datetime.now().isoformat(),
                    "reason": reason or "Optional phase skipped",
                    "phase": phase.name,
                    "phase_order": phase.order
                })
        
        output = [
            f'✓ Skipped Phase {phase_order}: {phase.name}',
            ''
        ]
        
        if reason:
            output.append(f'Reason: {reason}')
        
        output.append('')
        output.append('Next steps:')
        
        next_phase = self.get_next_phase(phase)
        if next_phase:
            code, msg = self.advance_to_next_phase(phase)
            if code == 0:
                output.append(msg)
        else:
            output.append('All phases complete or this was the last phase.')
        
        self.save_workflow_state()
        
        return 0, '\n'.join(output)
    
    def advance_to_next_phase(self, current_phase: Phase) -> Tuple[int, str]:
        next_phase = self.get_next_phase(current_phase)
        
        if not next_phase:
            self.workflow_state.status = WorkflowStatus.COMPLETE
            return 0, '🎉 All phases complete! Workflow finished.'
        
        output = [
            f'✓ Phase {current_phase.order} ({current_phase.name}) complete!',
            ''
        ]
        
        next_phase.status = PhaseStatus.ACTIVE
        next_phase.started_at = datetime.now().isoformat()
        self.workflow_state.current_phase = next_phase.order
        
        role_slug = self.to_slug(next_phase.role)
        feature_slug = self.to_slug(self.workflow_state.feature)
        short_id = datetime.now().strftime('%H%M%S')
        branch_name = f"{role_slug}/{feature_slug}-{short_id}"
        
        next_phase.branch = branch_name
        
        output.append(f'▶️ Phase {next_phase.order} ({next_phase.name}) is now active')
        output.append(f'Role: {next_phase.role}')
        output.append(f'Branch: {branch_name}')
        output.append('')
        output.append(f'To start: git checkout {branch_name}')
        output.append(f'Then: /git-flow commit <files>')
        
        return 0, '\n'.join(output)
    
    def phase_next(self) -> Tuple[int, str]:
        if not self.workflow_state:
            return 1, 'No workflow initialized.'
        
        if self.workflow_state.current_phase == 0:
            return 1, 'No active phase. Use /git-flow phase next to activate the first phase.'
        
        current_phase = self.workflow_state.phases[self.workflow_state.current_phase - 1]
        
        if not self.check_phase_complete(current_phase):
            return 1, f'Phase {current_phase.order} ({current_phase.name}) is not complete yet.'
        
        code, output = self.advance_to_next_phase(current_phase)
        
        self.save_workflow_state()
        
        return code, output
    
    def history(self) -> Tuple[int, str]:
        if not self.workflow_state:
            return 1, 'No workflow initialized.'
        
        output = [
            '📜 Git-Flow History',
            f'Feature: {self.workflow_state.feature}',
            ''
        ]
        
        for branch_name, branch in self.workflow_state.branches.items():
            phase = self.workflow_state.phases[branch.phase - 1]
            output.append(f'Branch: {branch_name}')
            output.append(f'  Role: {branch.role}')
            output.append(f'  Phase: {phase.order} - {phase.name}')
            output.append(f'  Status: {branch.status.value}')
            output.append(f'  Created: {branch.created_at}')
            
            if branch.review_history:
                output.append(f'  Review History:')
                for event in branch.review_history:
                    output.append(f'    - {event["action"]} by {event["actor"]} at {event["timestamp"]}')
                    if event.get("comment"):
                        output.append(f'      Comment: {event["comment"]}')
                    if event.get("reason"):
                        output.append(f'      Reason: {event["reason"]}')
            
            output.append('')
        
        return 0, '\n'.join(output)


def main():
    parser = argparse.ArgumentParser(
        description='Git-Flow Skill - Workflow Orchestration',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    start_parser = subparsers.add_parser('start', help='Start a new workflow')
    start_parser.add_argument('feature', help='Feature name')
    
    commit_parser = subparsers.add_parser('commit', help='Commit changes to current branch')
    commit_parser.add_argument('files', nargs='*', help='Files to commit')
    
    subparsers.add_parser('review', help='Show review dashboard')
    
    approve_parser = subparsers.add_parser('approve', help='Approve and merge a branch')
    approve_parser.add_argument('branch', help='Branch name')
    approve_parser.add_argument('--comment', help='Approval comment')
    
    reject_parser = subparsers.add_parser('reject', help='Reject a branch')
    reject_parser.add_argument('branch', help='Branch name')
    reject_parser.add_argument('--reason', required=True, help='Rejection reason')
    reject_parser.add_argument('--keep-branch', action='store_true', help='Keep branch after rejection')
    
    request_changes_parser = subparsers.add_parser('request-changes', help='Request changes on a branch')
    request_changes_parser.add_argument('branch', help='Branch name')
    request_changes_parser.add_argument('--comment', required=True, help='Comment for changes')
    
    unapprove_parser = subparsers.add_parser('unapprove', help='Unapprove a merged branch')
    unapprove_parser.add_argument('branch', help='Branch name')
    unapprove_parser.add_argument('--cascade', action='store_true', help='Revert all dependent branches')
    
    subparsers.add_parser('status', help='Show workflow status')
    
    subparsers.add_parser('phase-next', help='Advance to next phase')
        
    subparsers.add_parser('history', help='Show review history')
        
    resolve_parser = subparsers.add_parser('resolve', help='Resolve merge conflicts')
    resolve_parser.add_argument('strategy', choices=['abort', 'ours', 'theirs', 'manual'], 
                               help='Conflict resolution strategy')
        
    # Pipeline update commands    check_updates_parser = subparsers.add_parser('check-updates', help='Check for pipeline updates')
    
    update_parser = subparsers.add_parser('update', help='Update pipeline to new version')
    update_parser.add_argument('--to', help='Target version')
    update_parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    
    rollback_parser = subparsers.add_parser('rollback', help='Rollback pipeline to previous version')
    rollback_parser.add_argument('--to', required=True, help='Target version')
    rollback_parser.add_argument('--backup', help='Restore from specific backup')
    
    versions_parser = subparsers.add_parser('versions', help='List available pipeline versions')
    
    backups_parser = subparsers.add_parser('backups', help='List available backups')
    backups_parser.add_argument('--delete', help='Delete specific backup')
    backups_parser.add_argument('--cleanup', type=int, help='Delete old backups keeping N most recent')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    git_flow = GitFlow()
    
    if args.command == 'start':
        feature = InputSanitizer.sanitize_string(args.feature, allowed_chars=InputSanitizer.ALLOWED_ALPHANUMERIC, max_length=100)
        code, output = git_flow.start_workflow(feature)
    elif args.command == 'commit':
        files = [InputSanitizer.sanitize_file_path(f) for f in args.files] if args.files else []
        code, output = git_flow.commit(files)
    elif args.command == 'review':
        code, output = git_flow.review()
    elif args.command == 'approve':
        branch = InputSanitizer.sanitize_string(args.branch, allowed_chars=InputSanitizer.ALLOWED_BRANCH_CHARS, max_length=100)
        comment = InputSanitizer.sanitize_html(args.comment) if args.comment else None
        code, output = git_flow.review_approve(branch, comment)
    elif args.command == 'reject':
        branch = InputSanitizer.sanitize_string(args.branch, allowed_chars=InputSanitizer.ALLOWED_BRANCH_CHARS, max_length=100)
        reason = InputSanitizer.sanitize_html(args.reason)
        code, output = git_flow.review_reject(branch, reason, args.keep_branch)
    elif args.command == 'request-changes':
        branch = InputSanitizer.sanitize_string(args.branch, allowed_chars=InputSanitizer.ALLOWED_BRANCH_CHARS, max_length=100)
        comment = InputSanitizer.sanitize_html(args.comment)
        code, output = git_flow.review_request_changes(branch, comment)
    elif args.command == 'unapprove':
        branch = InputSanitizer.sanitize_string(args.branch, allowed_chars=InputSanitizer.ALLOWED_BRANCH_CHARS, max_length=100)
        code, output = git_flow.unapprove(branch, args.cascade)
    elif args.command == 'status':
        code, output = git_flow.status()
    elif args.command == 'phase-next':
        code, output = git_flow.phase_next()
    elif args.command == 'history':
        code, output = git_flow.history()
    elif args.command == 'resolve':
        code, output = git_flow.resolve_conflicts(args.strategy)
    elif args.command == 'check-updates':
        has_updates, latest = git_flow.pipeline_update_manager.check_for_updates()
        if has_updates:
            code, output = 0, f'Update available: {latest}\nCurrent version: {git_flow.pipeline_update_manager.get_current_version()}'
        else:
            code, output = 0, f'No updates available. Current version: {git_flow.pipeline_update_manager.get_current_version()}'
    elif args.command == 'update':
        target_version = args.to or git_flow.pipeline_update_manager.list_versions()[-1]
        state = git_flow.workflow_state.to_dict() if git_flow.workflow_state else {}
        code, output = git_flow.pipeline_update_manager.update_to_version(target_version, state, args.dry_run)
    elif args.command == 'rollback':
        state = git_flow.workflow_state.to_dict() if git_flow.workflow_state else {}
        code, output = git_flow.pipeline_update_manager.rollback_to_version(args.to, state, args.backup)
    elif args.command == 'versions':
        versions = git_flow.pipeline_update_manager.list_versions()
        current = git_flow.pipeline_update_manager.get_current_version()
        output_lines = ['Available versions:']
        for v in versions:
            marker = ' (current)' if v == current else ''
            output_lines.append(f'  - {v}{marker}')
        code, output = 0, '\n'.join(output_lines)
    elif args.command == 'backups':
        if args.delete:
            success = git_flow.pipeline_update_manager.backup_manager.delete_backup(args.delete)
            if success:
                code, output = 0, f'Deleted backup: {args.delete}'
            else:
                code, output = 1, f'Failed to delete backup: {args.delete}'
        elif args.cleanup:
            deleted = git_flow.pipeline_update_manager.backup_manager.cleanup_old_backups(args.cleanup)
            code, output = 0, f'Cleaned up {deleted} old backups'
        else:
            backups = git_flow.pipeline_update_manager.backup_manager.list_backups()
            output_lines = ['Available backups:']
            for backup in backups:
                output_lines.append(f"  - {backup['backup_id']}")
                output_lines.append(f"    Version: {backup.get('state_version', 'unknown')}")
                output_lines.append(f"    Timestamp: {backup.get('timestamp', 'unknown')}")
            code, output = 0, '\n'.join(output_lines)
    else:
        code, output = 1, f'Unknown command: {args.command}'
    
    # Initialize logger for CLI output
    logger = StructuredLogger(
        name="git-flow-cli",
        log_format=LogFormat.TEXT
    )
    logger.info(output)
    return code


if __name__ == '__main__':
    sys.exit(main())
