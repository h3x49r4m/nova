#!/usr/bin/env python3
"""
Git-Flow Review Module
Handles review, approval, and rejection operations.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from utils import (
    StructuredLogger,
    LogFormat,
    LogLevel
)
from .git_flow_config import GitFlowConfig
from .git_flow_branches import GitFlowBranches
from .models import ReviewEvent


class GitFlowReview:
    """Manages Git-Flow review and approval operations."""
    
    def __init__(self, config: GitFlowConfig, branches: GitFlowBranches):
        """
        Initialize review manager.
        
        Args:
            config: GitFlowConfig instance
            branches: GitFlowBranches instance
        """
        self.config = config
        self.branches = branches
        self.logger = config.logger
    
    def review(self) -> Tuple[int, str]:
        """
        Request a review for the current workflow.
        
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            if not self.config.workflow_state:
                return (1, "No active workflow to review")
            
            current_branch = self.branches.get_current_branch()
            feature = self.config.workflow_state.feature_name
            phase = self.config.workflow_state.current_phase.name
            
            # Create review request
            message = f"Review request for feature '{feature}'\n"
            message += f"Branch: {current_branch}\n"
            message += f"Phase: {phase}\n"
            message += f"Status: Pending review\n"
            message += f"\nUse 'git-flow review approve' to approve"
            
            self.logger.info(f"Review requested for feature '{feature}'")
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error requesting review: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def review_approve(self, branch_name: str, comment: Optional[str] = None) -> Tuple[int, str]:
        """
        Approve a review for a branch.
        
        Args:
            branch_name: Branch name to approve
            comment: Optional approval comment
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Check if branch exists
            if branch_name not in self.config.branch_states:
                return (1, f"Branch '{branch_name}' not found in workflow state")
            
            # Create review event
            event = ReviewEvent(
                event_id=self._generate_event_id(),
                timestamp=datetime.now().isoformat(),
                reviewer="system",
                approved=True,
                comment=comment or "Approved",
                gate=self.config.workflow_state.current_phase.name if self.config.workflow_state else "general"
            )
            
            # Add to workflow state
            if self.config.workflow_state:
                self.config.workflow_state.review_events.append(event)
                self.config.save_workflow_state()
            
            message = f"Approved branch '{branch_name}'"
            if comment:
                message += f"\nComment: {comment}"
            
            self.logger.info(f"Approved branch '{branch_name}'")
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error approving review: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def review_reject(self, branch_name: str, reason: str, keep_branch: bool = True) -> Tuple[int, str]:
        """
        Reject a review for a branch.
        
        Args:
            branch_name: Branch name to reject
            reason: Rejection reason
            keep_branch: If True, keep the branch for fixes
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Check if branch exists
            if branch_name not in self.config.branch_states:
                return (1, f"Branch '{branch_name}' not found in workflow state")
            
            # Create review event
            event = ReviewEvent(
                event_id=self._generate_event_id(),
                timestamp=datetime.now().isoformat(),
                reviewer="system",
                approved=False,
                comment=reason,
                gate=self.config.workflow_state.current_phase.name if self.config.workflow_state else "general"
            )
            
            # Add to workflow state
            if self.config.workflow_state:
                self.config.workflow_state.review_events.append(event)
                self.config.workflow_state.status = "REJECTED"
                self.config.save_workflow_state()
            
            # Delete branch if not keeping
            if not keep_branch:
                code, msg = self.branches.delete_branch(branch_name, force=True)
                if code != 0:
                    return (code, f"Rejected but failed to delete branch: {msg}")
            
            message = f"Rejected branch '{branch_name}'\n"
            message += f"Reason: {reason}\n"
            message += f"Branch {'kept' if keep_branch else 'deleted'}"
            
            self.logger.info(f"Rejected branch '{branch_name}'")
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error rejecting review: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def review_request_changes(self, branch_name: str, comment: str) -> Tuple[int, str]:
        """
        Request changes for a branch review.
        
        Args:
            branch_name: Branch name to request changes for
            comment: Comment explaining required changes
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Check if branch exists
            if branch_name not in self.config.branch_states:
                return (1, f"Branch '{branch_name}' not found in workflow state")
            
            # Create review event
            event = ReviewEvent(
                event_id=self._generate_event_id(),
                timestamp=datetime.now().isoformat(),
                reviewer="system",
                approved=False,
                comment=f"Changes requested: {comment}",
                gate=self.config.workflow_state.current_phase.name if self.config.workflow_state else "general"
            )
            
            # Add to workflow state
            if self.config.workflow_state:
                self.config.workflow_state.review_events.append(event)
                self.config.save_workflow_state()
            
            message = f"Changes requested for branch '{branch_name}'\n"
            message += f"Comment: {comment}"
            
            self.logger.info(f"Changes requested for branch '{branch_name}'")
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error requesting changes: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def unapprove(self, branch_name: str, cascade: bool = False) -> Tuple[int, str]:
        """
        Remove approval from a branch.
        
        Args:
            branch_name: Branch name to unapprove
            cascade: If True, cascade unapproval to dependent branches
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Check if branch exists
            if branch_name not in self.config.branch_states:
                return (1, f"Branch '{branch_name}' not found in workflow state")
            
            # Check if unapproval is allowed after merge
            allow_after_merge = self.config.get_config_value(
                'unapproval', 'allow_unapprove_after_merge', default=True
            )
            
            branch_state = self.config.branch_states.get(branch_name)
            if not allow_after_merge and branch_state and branch_state.merged:
                return (1, "Cannot unapprove after merge (disabled in config)")
            
            # Remove approval from review events
            if self.config.workflow_state:
                self.config.workflow_state.review_events = [
                    event for event in self.config.workflow_state.review_events
                    if not (event.approved and event.gate == branch_name)
                ]
                self.config.save_workflow_state()
            
            message = f"Unapproved branch '{branch_name}'"
            
            # Cascade to dependent branches if enabled
            if cascade:
                dependents = self._get_dependent_branches(branch_name)
                if dependents:
                    for dep in dependents:
                        self.unapprove(dep, cascade=True)
                    message += f"\nCascaded to {len(dependents)} dependent branches"
            
            self.logger.info(f"Unapproved branch '{branch_name}'")
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error unapproving: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def revert_branch(self, branch_name: str) -> str:
        """
        Revert a branch to its pre-merge state.
        
        Args:
            branch_name: Branch name to revert
            
        Returns:
            Message describing the revert operation
        """
        try:
            # Check if branch exists
            if branch_name not in self.config.branch_states:
                return f"Branch '{branch_name}' not found in workflow state"
            
            branch_state = self.config.branch_states.get(branch_name)
            if not branch_state or not branch_state.merged:
                return f"Branch '{branch_name}' has not been merged, cannot revert"
            
            # Get the merge commit
            merge_commit = branch_state.merge_commit
            if not merge_commit:
                return "No merge commit found, cannot revert"
            
            # Revert the merge
            code, stdout, stderr = self.config.run_git_command(
                ['revert', '-m', '1', merge_commit, '--no-edit'],
                cwd=self.repo_root
            )
            
            if code != 0:
                return f"Failed to revert merge: {stderr}"
            
            # Update branch state
            branch_state.merged = False
            branch_state.merge_commit = None
            self.config.save_branch_states()
            
            message = f"Reverted branch '{branch_name}' (commit {merge_commit})"
            self.logger.info(message)
            return message
            
        except Exception as e:
            error_msg = f"Error reverting branch: {e}"
            self.logger.error(error_msg)
            return error_msg
    
    def get_review_history(self, branch_name: Optional[str] = None) -> Tuple[int, str]:
        """
        Get review history for a branch or all branches.
        
        Args:
            branch_name: Optional branch name to filter by
            
        Returns:
            Tuple of (exit_code, message)
        """
        try:
            if not self.config.workflow_state:
                return (1, "No active workflow")
            
            events = self.config.workflow_state.review_events
            
            # Filter by branch if specified
            if branch_name:
                events = [e for e in events if e.gate == branch_name]
            
            if not events:
                return (0, "No review events found")
            
            # Format events
            message = f"Review History ({len(events)} events):\n\n"
            for event in events:
                status = "✓ APPROVED" if event.approved else "✗ REJECTED"
                message += f"[{event.timestamp}] {status}\n"
                message += f"  Reviewer: {event.reviewer}\n"
                message += f"  Gate: {event.gate}\n"
                if event.comment:
                    message += f"  Comment: {event.comment}\n"
                message += "\n"
            
            return (0, message)
            
        except Exception as e:
            error_msg = f"Error getting review history: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
    
    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"review_{timestamp}"
    
    def _get_dependent_branches(self, branch_name: str) -> List[str]:
        """
        Get branches that depend on the given branch.
        
        Args:
            branch_name: Branch name to check
            
        Returns:
            List of dependent branch names
        """
        dependents = []
        
        for branch, state in self.config.branch_states.items():
            if branch_name in state.dependencies:
                dependents.append(branch)
        
        return dependents
