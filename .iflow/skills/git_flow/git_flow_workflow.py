#!/usr/bin/env python3
"""
Git-Flow Workflow Control Module
Handles workflow control, phase management, and workflow state transitions.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from utils import (
    StructuredLogger,
    LogFormat,
    LogLevel,
    WorkflowStatus,
    PhaseStatus
)
from .git_flow_config import GitFlowConfig
from .git_flow_branches import GitFlowBranches
from .models import WorkflowState, Phase


class GitFlowWorkflow:
    """Manages Git-Flow workflow operations and phase transitions."""
    
    def __init__(self, config: GitFlowConfig, branches: GitFlowBranches):
        """
        Initialize workflow manager.
        
        Args:
            config: GitFlowConfig instance
            branches: GitFlowBranches instance
        """
        self.config = config
        self.branches = branches
        self.logger = config.logger
    
    def start_workflow(self, feature: str, resume: bool = False) -> Tuple[int, str]:
        """
        Start a new workflow for a feature.
        
        Args:
            feature: Feature description
            resume: If True, resume existing workflow
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Check if workflow already exists
            if self.config.workflow_state and not resume:
                return (1, "Workflow already in progress. Use --resume to continue.")
            
            # Resume existing workflow
            if resume and self.config.workflow_state:
                return self.resume_workflow()
            
            # Detect role
            auto_detect = self.config.get_config_value('workflow', 'auto_detect_role', default=True)
            role = self.branches.detect_role() if auto_detect else 'general'
            
            # Generate branch name
            auto_create = self.config.get_config_value('workflow', 'auto_create_branch', default=True)
            branch_name = self.branches.generate_branch_name(role, feature)
            
            # Create branch if enabled
            if auto_create:
                code, msg = self.branches.create_branch(branch_name)
                if code != 0:
                    return (code, msg)
            
            # Initialize workflow state
            first_phase = self.config.get_phase_by_order(1)
            if not first_phase:
                return (1, "No phases configured")
            
            self.config.workflow_state = WorkflowState(
                feature_name=feature,
                branch_name=branch_name,
                current_phase=Phase(
                    order=first_phase['order'],
                    name=first_phase['name'],
                    status=PhaseStatus.IN_PROGRESS,
                    started_at=datetime.now().isoformat()
                ),
                status=WorkflowStatus.IN_PROGRESS,
                started_at=datetime.now().isoformat(),
                review_events=[],
                completed_phases=[]
            )
            
            self.config.save_workflow_state()
            
            message = f"Started workflow for feature '{feature}'\n"
            message += f"Branch: {branch_name}\n"
            message += f"Current phase: {first_phase['name']}"
            
            self.logger.info(f"Started workflow for feature '{feature}'")
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error starting workflow: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def resume_workflow(self) -> Tuple[int, str]:
        """
        Resume an existing workflow.
        
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            if not self.config.workflow_state:
                return (1, "No existing workflow to resume")
            
            # Switch to workflow branch
            code, msg = self.branches.switch_branch(self.config.workflow_state.branch_name)
            if code != 0:
                return (code, f"Failed to switch to workflow branch: {msg}")
            
            # Check phase timeout
            current_phase = self.config.workflow_state.current_phase
            timed_out, timeout_msg = self.check_phase_timeout(current_phase)
            if timed_out:
                self.logger.warning(f"Phase timeout detected: {timeout_msg}")
            
            message = f"Resumed workflow for feature '{self.config.workflow_state.feature_name}'\n"
            message += f"Branch: {self.config.workflow_state.branch_name}\n"
            message += f"Current phase: {current_phase.name} (Status: {current_phase.status.value})"
            
            self.logger.info("Resumed workflow")
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error resuming workflow: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def commit(self, files: List[str]) -> Tuple[int, str]:
        """
        Commit changes with workflow context.
        
        Args:
            files: List of files to commit
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            if not self.config.workflow_state:
                return (1, "No active workflow. Start a workflow first.")
            
            # Add files
            for file in files:
                code, stdout, stderr = self.config.run_git_command(
                    ['add', file],
                    cwd=self.repo_root
                )
                if code != 0:
                    return (code, f"Failed to add file '{file}': {stderr}")
            
            # Create commit message
            feature = self.config.workflow_state.feature_name
            phase = self.config.workflow_state.current_phase.name
            commit_msg = f"[{feature}] {phase}: Update files"
            
            # Commit
            code, stdout, stderr = self.config.run_git_command(
                ['commit', '-m', commit_msg],
                cwd=self.repo_root
            )
            
            if code != 0:
                return (code, f"Failed to commit: {stderr}")
            
            self.logger.info(f"Committed {len(files)} files")
            return (0, f"Committed {len(files)} files to '{self.branches.get_current_branch()}'")
            
        except Exception as e:
            error_msg = f"Error committing: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def check_phase_timeout(self, phase: Phase) -> Tuple[bool, Optional[str]]:
        """
        Check if a phase has timed out.
        
        Args:
            phase: Phase to check
            
        Returns:
            Tuple of (is_timed_out, timeout_message)
        """
        if not phase.started_at:
            return (False, None)
        
        try:
            start_time = datetime.fromisoformat(phase.started_at)
            timeout_hours = self.config.get_config_value(
                'timeouts', 'phase_timeout_hours', default=168
            )
            
            elapsed = datetime.now() - start_time
            timeout = timedelta(hours=timeout_hours)
            
            if elapsed > timeout:
                msg = f"Phase '{phase.name}' exceeded timeout of {timeout_hours} hours"
                return (True, msg)
            
            return (False, None)
            
        except Exception as e:
            self.logger.warning(f"Error checking phase timeout: {e}")
            return (False, None)
    
    def enforce_phase_timeouts(self) -> Tuple[int, str]:
        """
        Check and enforce phase timeouts across all active workflows.
        
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            if not self.config.workflow_state:
                return (0, "No active workflow")
            
            current_phase = self.config.workflow_state.current_phase
            timed_out, timeout_msg = self.check_phase_timeout(current_phase)
            
            if timed_out:
                # Update phase status
                current_phase.status = PhaseStatus.TIMED_OUT
                self.config.workflow_state.status = WorkflowStatus.BLOCKED
                
                self.config.save_workflow_state()
                
                message = f"Phase timeout detected:\n{timeout_msg}\n"
                message += f"Workflow status set to BLOCKED"
                
                self.logger.warning(message)
                return (0, message)
            
            return (0, "No phase timeouts detected")
            
        except Exception as e:
            error_msg = f"Error enforcing phase timeouts: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def check_phase_complete(self, phase: Phase) -> bool:
        """
        Check if a phase is complete based on its gates.
        
        Args:
            phase: Phase to check
            
        Returns:
            True if phase is complete
        """
        try:
            # Get phase definition
            phase_def = self.config.get_phase_by_order(phase.order)
            if not phase_def:
                return False
            
            # Check required gates
            required_gates = phase_def.get('required_gates', [])
            
            # Check if all required gates are passed
            for gate in required_gates:
                gate_passed = self._check_gate_passed(gate)
                if not gate_passed:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking phase completion: {e}")
            return False
    
    def _check_gate_passed(self, gate_name: str) -> bool:
        """
        Check if a specific gate has been passed.
        
        Args:
            gate_name: Name of the gate to check
            
        Returns:
            True if gate is passed
        """
        # Check review events for this gate
        if not self.config.workflow_state:
            return False
        
        for event in self.config.workflow_state.review_events:
            if event.gate == gate_name and event.approved:
                return True
        
        return False
    
    def get_next_phase(self, current_phase: Phase) -> Optional[Phase]:
        """
        Get the next phase in the workflow.
        
        Args:
            current_phase: Current phase
            
        Returns:
            Next phase or None if current is last
        """
        all_phases = self.config.get_all_phases()
        
        for i, phase_def in enumerate(all_phases):
            if phase_def['order'] == current_phase.order:
                if i + 1 < len(all_phases):
                    next_def = all_phases[i + 1]
                    return Phase(
                        order=next_def['order'],
                        name=next_def['name'],
                        status=PhaseStatus.PENDING
                    )
        
        return None
    
    def advance_to_next_phase(self, current_phase: Phase) -> Tuple[int, str]:
        """
        Advance workflow to the next phase.
        
        Args:
            current_phase: Current phase to advance from
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Check if current phase is complete
            if not self.check_phase_complete(current_phase):
                return (1, f"Phase '{current_phase.name}' is not complete")
            
            # Get next phase
            next_phase = self.get_next_phase(current_phase)
            if not next_phase:
                return (1, "Already at final phase")
            
            # Complete current phase
            current_phase.status = PhaseStatus.COMPLETED
            current_phase.completed_at = datetime.now().isoformat()
            
            if self.config.workflow_state:
                self.config.workflow_state.completed_phases.append(current_phase)
            
            # Start next phase
            next_phase.status = PhaseStatus.IN_PROGRESS
            next_phase.started_at = datetime.now().isoformat()
            
            if self.config.workflow_state:
                self.config.workflow_state.current_phase = next_phase
            
            self.config.save_workflow_state()
            
            message = f"Advanced from '{current_phase.name}' to '{next_phase.name}'"
            self.logger.info(message)
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error advancing phase: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def phase_next(self) -> Tuple[int, str]:
        """
        Advance to the next phase in the workflow.
        
        Returns:
            Tuple of (exit_code, message)
        """
        if not self.config.workflow_state:
            return (1, "No active workflow")
        
        current_phase = self.config.workflow_state.current_phase
        return self.advance_to_next_phase(current_phase)
    
    def skip_phase(self, phase_order: int, reason: Optional[str] = None) -> Tuple[int, str]:
        """
        Skip a specific phase.
        
        Args:
            phase_order: Order number of phase to skip
            reason: Reason for skipping
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            if not self.config.workflow_state:
                return (1, "No active workflow")
            
            current_phase = self.config.workflow_state.current_phase
            
            # Check if skipping the requested phase
            if current_phase.order != phase_order:
                return (1, f"Cannot skip phase {phase_order} (current: {current_phase.order})")
            
            # Mark current phase as skipped
            current_phase.status = PhaseStatus.SKIPPED
            current_phase.skipped_reason = reason
            
            if self.config.workflow_state:
                self.config.workflow_state.completed_phases.append(current_phase)
            
            # Advance to next phase
            return self.advance_to_next_phase(current_phase)
            
        except Exception as e:
            error_msg = f"Error skipping phase: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def get_workflow_status(self) -> Dict:
        """
        Get current workflow status.
        
        Returns:
            Dictionary with workflow status information
        """
        if not self.config.workflow_state:
            return {
                'status': 'NO_WORKFLOW',
                'message': 'No active workflow'
            }
        
        state = self.config.workflow_state
        
        return {
            'feature': state.feature_name,
            'branch': state.branch_name,
            'status': state.status.value,
            'current_phase': {
                'order': state.current_phase.order,
                'name': state.current_phase.name,
                'status': state.current_phase.status.value
            },
            'started_at': state.started_at,
            'completed_phases': len(state.completed_phases),
            'review_events': len(state.review_events)
        }
