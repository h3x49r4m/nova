#!/usr/bin/env python3
"""
Git-Flow Configuration Module
Handles configuration loading, merging, and state management.
"""

from typing import TYPE_CHECKING, Any

from utils import (
    LogFormat,
    LogLevel,
    StructuredLogger,
    read_locked_json,
)

from .models import BranchState, WorkflowState

if TYPE_CHECKING:
    from pathlib import Path


class GitFlowConfig:
    """Manages Git-Flow configuration and state persistence."""

    def __init__(self, repo_root: Path, skill_dir: Path, dry_run: bool = False):
        """
        Initialize configuration manager.

        Args:
            repo_root: Repository root path
            skill_dir: Git-flow skill directory path
            dry_run: If True, operations will not actually execute
        """
        self.repo_root = repo_root
        self.skill_dir = skill_dir
        self.dry_run = dry_run

        self.config_file = self.skill_dir / 'config.json'
        self.phases_file = self.skill_dir / 'phases.json'
        self.workflow_state_file = self.skill_dir / 'workflow-state.json'
        self.branch_states_file = self.skill_dir / 'branch-states.json'

        self.logger = StructuredLogger(
            name="git-flow-config",
            log_dir=self.repo_root / ".iflow" / "logs",
            log_level=LogLevel.INFO,
            log_format=LogFormat.JSON
        )

        self.config: dict = {}
        self.phases: dict = {}
        self.workflow_state: WorkflowState | None = None
        self.branch_states: dict[str, BranchState] = {}

    def load_config(self) -> None:
        """Load configuration from config.json file."""
        default_config = {
            "workflow": {
                "auto_detect_role": True,
                "auto_create_branch": True,
                "auto_phase_transition": True,
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
                "require_reason": False
            },
            "timeouts": {
                "phase_timeout_hours": 168,
                "merge_timeout_minutes": 30,
                "review_timeout_days": 7
            },
            "notifications": {
                "enabled": False,
                "on_review": False,
                "on_merge": False,
                "on_error": True
            }
        }

        if self.config_file.exists():
            try:
                user_config = read_locked_json(self.config_file)
                self.config = self._merge_config(default_config, user_config)
                self.logger.info("Configuration loaded successfully")
            except Exception as e:
                self.logger.warning(f"Failed to load config, using defaults: {e}")
                self.config = default_config
        else:
            self.config = default_config
            self.logger.info("Using default configuration")

    def _merge_config(self, default: dict, user: dict) -> dict:
        """
        Merge user configuration with defaults.

        Args:
            default: Default configuration dictionary
            user: User configuration dictionary

        Returns:
            Merged configuration dictionary
        """
        result = default.copy()

        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value

        return result

    def load_phases(self) -> None:
        """Load phase definitions from phases.json file."""
        default_phases = {
            "phases": [
                {
                    "order": 1,
                    "name": "planning",
                    "description": "Planning and requirements gathering",
                    "required_gates": [],
                    "timeout_hours": 24
                },
                {
                    "order": 2,
                    "name": "development",
                    "description": "Implementation and coding",
                    "required_gates": [],
                    "timeout_hours": 168
                },
                {
                    "order": 3,
                    "name": "testing",
                    "description": "Testing and quality assurance",
                    "required_gates": ["code_review", "unit_tests"],
                    "timeout_hours": 48
                },
                {
                    "order": 4,
                    "name": "review",
                    "description": "Final review and approval",
                    "required_gates": ["final_approval"],
                    "timeout_hours": 24
                }
            ]
        }

        if self.phases_file.exists():
            try:
                self.phases = read_locked_json(self.phases_file)
                self.logger.info("Phases loaded successfully")
            except Exception as e:
                self.logger.warning(f"Failed to load phases, using defaults: {e}")
                self.phases = default_phases
        else:
            self.phases = default_phases
            self.logger.info("Using default phases")

    def load_workflow_state(self) -> None:
        """Load workflow state from workflow-state.json file."""
        if self.workflow_state_file.exists():
            try:
                state_data = read_locked_json(self.workflow_state_file)
                self.workflow_state = WorkflowState.from_dict(state_data)
                self.logger.info("Workflow state loaded successfully")
            except Exception as e:
                self.logger.warning(f"Failed to load workflow state: {e}")
                self.workflow_state = None
        else:
            self.workflow_state = None
            self.logger.info("No existing workflow state")

    def load_branch_states(self) -> None:
        """Load branch states from branch-states.json file."""
        if self.branch_states_file.exists():
            try:
                states_data = read_locked_json(self.branch_states_file)
                self.branch_states = {
                    branch: BranchState.from_dict(state_data)
                    for branch, state_data in states_data.items()
                }
                self.logger.info(f"Loaded {len(self.branch_states)} branch states")
            except Exception as e:
                self.logger.warning(f"Failed to load branch states: {e}")
                self.branch_states = {}
        else:
            self.branch_states = {}
            self.logger.info("No existing branch states")

    def save_workflow_state(self) -> None:
        """Save workflow state to workflow-state.json file."""
        if self.workflow_state:
            try:
                state_dict = self.workflow_state.to_dict()
                # Use write_locked_json for thread-safe writing
                from utils import write_locked_json
                write_locked_json(self.workflow_state_file, state_dict)
                self.logger.info("Workflow state saved successfully")
            except Exception as e:
                self.logger.error(f"Failed to save workflow state: {e}")

    def save_branch_states(self) -> None:
        """Save branch states to branch-states.json file."""
        try:
            states_dict = {
                branch: state.to_dict()
                for branch, state in self.branch_states.items()
            }
            from utils import write_locked_json
            write_locked_json(self.branch_states_file, states_dict)
            self.logger.info(f"Saved {len(self.branch_states)} branch states")
        except Exception as e:
            self.logger.error(f"Failed to save branch states: {e}")

    def get_config_value(self, *keys: str, default: Any = None) -> Any:
        """
        Get a configuration value by nested keys.

        Args:
            *keys: Nested keys to traverse the config
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_phase_by_order(self, order: int) -> dict | None:
        """
        Get phase definition by order number.

        Args:
            order: Phase order number

        Returns:
            Phase dictionary or None
        """
        for phase in self.phases.get("phases", []):
            if phase.get("order") == order:
                return phase
        return None

    def get_all_phases(self) -> list:
        """
        Get all phases sorted by order.

        Returns:
            List of phase dictionaries
        """
        phases = self.phases.get("phases", [])
        return sorted(phases, key=lambda p: p.get("order", 0))
