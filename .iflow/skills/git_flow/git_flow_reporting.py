#!/usr/bin/env python3
"""
Git-Flow Reporting Module
Handles status reporting and history operations.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from utils import run_git_command

if TYPE_CHECKING:
    from .git_flow_branches import GitFlowBranches
    from .git_flow_config import GitFlowConfig
    from .git_flow_merge import GitFlowMerge


class GitFlowReporting:
    """Manages Git-Flow reporting and status operations."""

    def __init__(self, config: GitFlowConfig, branches: GitFlowBranches, merge_manager: GitFlowMerge):
        """
        Initialize reporting manager.

        Args:
            config: GitFlowConfig instance
            branches: GitFlowBranches instance
            merge_manager: GitFlowMerge instance
        """
        self.config = config
        self.branches = branches
        self.merge_manager = merge_manager
        self.logger = config.logger
        self.repo_root = config.repo_root

    def status(self) -> tuple[int, str]:
        """
        Get current workflow and repository status.

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Get current branch
            current_branch = self.branches.get_current_branch()

            # Get git status
            code, stdout, _stderr = run_git_command(
                ['status', '--short'],
                cwd=self.repo_root
            )
            git_status = stdout.strip() if code == 0 else "Error getting status"

            # Build status report
            message = "=== Git-Flow Status ===\n\n"

            # Repository info
            message += "Repository:\n"
            message += f"  Current Branch: {current_branch}\n"
            message += f"  Root: {self.repo_root}\n\n"

            # Workflow status
            if self.config.workflow_state:
                state = self.config.workflow_state
                message += "Workflow:\n"
                message += f"  Feature: {state.feature_name}\n"
                message += f"  Branch: {state.branch_name}\n"
                message += f"  Status: {state.status.value}\n"
                message += f"  Started: {state.started_at}\n"
                message += f"  Current Phase: {state.current_phase.name}\n"
                message += f"  Phase Status: {state.current_phase.status.value}\n"
                message += f"  Completed Phases: {len(state.completed_phases)}\n"
                message += f"  Review Events: {len(state.review_events)}\n\n"
            else:
                message += "Workflow: No active workflow\n\n"

            # Branch status
            message += "Branches:\n"
            message += f"  Tracked: {len(self.config.branch_states)}\n\n"

            # Git status
            message += "Git Status:\n"
            if git_status:
                for line in git_status.split('\n'):
                    if line.strip():
                        message += f"  {line}\n"
            else:
                message += "  Working directory clean\n"

            self.logger.info("Status report generated")
            return (0, message)

        except Exception as e:
            error_msg = f"Error getting status: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)

    def history(self) -> tuple[int, str]:
        """
        Get workflow and commit history.

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            message = "=== Git-Flow History ===\n\n"

            # Workflow history
            if self.config.workflow_state:
                state = self.config.workflow_state

                message += "Workflow History:\n"
                message += f"  Started: {state.started_at}\n"
                message += f"  Feature: {state.feature_name}\n\n"

                # Phase history
                if state.completed_phases:
                    message += "Completed Phases:\n"
                    for phase in state.completed_phases:
                        message += f"  - {phase.name} (Order: {phase.order})\n"
                        if phase.completed_at:
                            message += f"    Completed: {phase.completed_at}\n"
                    message += "\n"

                # Review history
                if state.review_events:
                    message += "Review Events:\n"
                    for event in state.review_events:
                        status = "✓ APPROVED" if event.approved else "✗ REJECTED"
                        message += f"  - [{event.timestamp}] {status}\n"
                        message += f"    Reviewer: {event.reviewer}\n"
                        message += f"    Gate: {event.gate}\n"
                        if event.comment:
                            message += f"    Comment: {event.comment}\n"
                    message += "\n"

            # Git history
            message += "Recent Commits:\n"
            code, stdout, _stderr = run_git_command(
                ['log', '--oneline', '-10'],
                cwd=self.repo_root
            )

            if code == 0:
                for line in stdout.strip().split('\n'):
                    if line.strip():
                        message += f"  {line}\n"
            else:
                message += "  Error getting commit history\n"

            self.logger.info("History report generated")
            return (0, message)

        except Exception as e:
            error_msg = f"Error getting history: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)

    def get_branch_report(self, branch_name: str | None = None) -> tuple[int, str]:
        """
        Get a detailed report for a specific branch or all branches.

        Args:
            branch_name: Optional branch name to report on

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            message = "=== Branch Report ===\n\n"

            if branch_name:
                # Single branch report
                if branch_name not in self.config.branch_states:
                    return (1, f"Branch '{branch_name}' not found in workflow state")

                state = self.config.branch_states[branch_name]
                message += f"Branch: {branch_name}\n"
                message += f"  Status: {state.status.value}\n"
                message += f"  Created: {state.created_at}\n"
                message += f"  Merged: {state.merged}\n"
                if state.merged_at:
                    message += f"  Merged At: {state.merged_at}\n"
                if state.merge_commit:
                    message += f"  Merge Commit: {state.merge_commit}\n"
                if state.dependencies:
                    message += f"  Dependencies: {', '.join(state.dependencies)}\n"

                # Get git info
                code, stdout, _stderr = run_git_command(
                    ['log', '--oneline', '-5', branch_name],
                    cwd=self.repo_root
                )
                if code == 0:
                    message += "\n  Recent Commits:\n"
                    for line in stdout.strip().split('\n'):
                        if line.strip():
                            message += f"    {line}\n"
            else:
                # All branches report
                message += f"Total Tracked Branches: {len(self.config.branch_states)}\n\n"

                for branch_name, state in self.config.branch_states.items():
                    message += f"Branch: {branch_name}\n"
                    message += f"  Status: {state.status.value}\n"
                    message += f"  Created: {state.created_at}\n"
                    if state.merged:
                        message += f"  Merged: Yes ({state.merged_at})\n"
                    if state.dependencies:
                        message += f"  Dependencies: {', '.join(state.dependencies)}\n"
                    message += "\n"

            self.logger.info("Branch report generated")
            return (0, message)

        except Exception as e:
            error_msg = f"Error getting branch report: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)

    def get_dependency_report(self) -> tuple[int, str]:
        """
        Get a comprehensive dependency report.

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            dep_report = self.merge_manager.get_dependency_report()

            message = "=== Dependency Report ===\n\n"
            message += f"Total Branches: {dep_report['total_branches']}\n"
            message += f"Branches with Dependencies: {dep_report['branches_with_dependencies']}\n\n"

            if dep_report['dependency_graph']:
                message += "Dependency Graph:\n"
                for branch, deps in dep_report['dependency_graph'].items():
                    message += f"  {branch}:\n"
                    for dep in deps:
                        message += f"    - {dep}\n"
                message += "\n"

            if dep_report['deadlocks']:
                message += "Deadlocks Detected:\n"
                for deadlock in dep_report['deadlocks']:
                    message += f"  - Branch: {deadlock['branch']}\n"
                    message += f"    Type: {deadlock['type']}\n"
            else:
                message += "No deadlocks detected\n"

            self.logger.info("Dependency report generated")
            return (0, message)

        except Exception as e:
            error_msg = f"Error getting dependency report: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)

    def get_statistics(self) -> dict[str, Any]:
        """
        Get comprehensive statistics about the workflow.

        Returns:
            Dictionary with statistics
        """
        try:
            stats = {
                'workflow': {
                    'has_active_workflow': self.config.workflow_state is not None,
                    'started_at': self.config.workflow_state.started_at if self.config.workflow_state else None,
                    'current_phase': self.config.workflow_state.current_phase.name if self.config.workflow_state else None,
                    'completed_phases': len(self.config.workflow_state.completed_phases) if self.config.workflow_state else 0,
                    'review_events': len(self.config.workflow_state.review_events) if self.config.workflow_state else 0
                },
                'branches': {
                    'total': len(self.config.branch_states),
                    'active': sum(1 for s in self.config.branch_states.values() if s.status.value == 'active'),
                    'merged': sum(1 for s in self.config.branch_states.values() if s.merged),
                    'failed': sum(1 for s in self.config.branch_states.values() if s.status.value == 'failed')
                },
                'repository': {
                    'current_branch': self.branches.get_current_branch(),
                    'protected_branches': list(self.branches.PROTECTED_BRANCHES)
                },
                'timestamp': datetime.now().isoformat()
            }

            return stats

        except Exception as e:
            self.logger.error(f"Error getting statistics: {e}")
            return {}

    def get_activity_report(self, days: int = 7) -> tuple[int, str]:
        """
        Get an activity report for the specified number of days.

        Args:
            days: Number of days to include in report

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Get recent commits
            since_date = datetime.now().timestamp() - (days * 24 * 60 * 60)

            code, stdout, _stderr = run_git_command(
                ['log', '--since', str(int(since_date)), '--pretty=format:%h|%an|%ad|%s', '--date=iso'],
                cwd=self.repo_root
            )

            message = f"=== Activity Report (Last {days} Days) ===\n\n"

            if code == 0 and stdout.strip():
                commits = stdout.strip().split('\n')
                message += f"Total Commits: {len(commits)}\n\n"

                # Group by author
                authors = {}
                for commit in commits:
                    parts = commit.split('|', 3)
                    if len(parts) >= 3:
                        author = parts[1]
                        authors[author] = authors.get(author, 0) + 1

                message += "Commits by Author:\n"
                for author, count in sorted(authors.items(), key=lambda x: x[1], reverse=True):
                    message += f"  {author}: {count}\n"

                message += "\nRecent Commits:\n"
                for commit in commits[:10]:
                    parts = commit.split('|', 3)
                    if len(parts) >= 4:
                        message += f"  {parts[0]} - {parts[1]} ({parts[2][:10]}): {parts[3][:60]}\n"
            else:
                message += "No commits in the specified period\n"

            self.logger.info("Activity report generated")
            return (0, message)

        except Exception as e:
            error_msg = f"Error getting activity report: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)
