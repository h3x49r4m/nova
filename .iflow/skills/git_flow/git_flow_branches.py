#!/usr/bin/env python3
"""
Git-Flow Branch Management Module
Handles branch creation, deletion, and management operations.
"""

import re
from pathlib import Path
from typing import TYPE_CHECKING

from utils import (
    BranchStatus,
    GitError,
    get_current_branch,
    run_git_command,
    validate_branch_name,
)

from .models import BranchState

if TYPE_CHECKING:
    from .git_flow_config import GitFlowConfig


class GitFlowBranches:
    """Manages Git-Flow branch operations."""

    # Protected branch names
    PROTECTED_BRANCHES = {'main', 'master', 'develop', 'production', 'staging'}

    def __init__(self, config: GitFlowConfig, repo_root: Path):
        """
        Initialize branch manager.

        Args:
            config: GitFlowConfig instance
            repo_root: Repository root path
        """
        self.config = config
        self.repo_root = repo_root
        self.logger = config.logger

    def get_current_branch(self) -> str:
        """
        Get the current branch name.

        Returns:
            Current branch name
        """
        try:
            return get_current_branch(self.repo_root)
        except GitError as e:
            self.logger.error(f"Failed to get current branch: {e}")
            raise

    def is_protected_branch(self, branch: str) -> bool:
        """
        Check if a branch is protected.

        Args:
            branch: Branch name to check

        Returns:
            True if branch is protected
        """
        return branch.lower() in self.PROTECTED_BRANCHES

    def detect_role(self) -> str:
        """
        Detect the current user's role from directory structure.

        Returns:
            Detected role name
        """
        try:
            # Check if we're in a role-specific directory
            current_path = Path.cwd()

            # Look for role indicators in path
            role_patterns = {
                'frontend': ['frontend', 'ui', 'web', 'client'],
                'backend': ['backend', 'api', 'server', 'service'],
                'devops': ['devops', 'infrastructure', 'deploy', 'ci'],
                'testing': ['test', 'qa', 'testing', 'quality'],
                'documentation': ['docs', 'documentation', 'wiki'],
                'security': ['security', 'sec', 'audit']
            }

            path_str = str(current_path).lower()

            for role, patterns in role_patterns.items():
                if any(pattern in path_str for pattern in patterns):
                    return role

            # Default to 'general' if no pattern matches
            return 'general'

        except Exception as e:
            self.logger.warning(f"Failed to detect role: {e}")
            return 'general'

    def to_slug(self, text: str) -> str:
        """
        Convert text to URL-friendly slug.

        Args:
            text: Text to convert

        Returns:
            Slug string
        """
        # Convert to lowercase and replace spaces with hyphens
        slug = text.lower().replace(' ', '-')
        # Remove special characters except hyphens and alphanumeric
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        return slug

    def generate_branch_name(self, role: str, feature: str) -> str:
        """
        Generate a branch name from role and feature.

        Args:
            role: Role name
            feature: Feature description

        Returns:
            Generated branch name
        """
        feature_slug = self.to_slug(feature)
        role_slug = self.to_slug(role)
        return f"{role_slug}/{feature_slug}"

    def create_branch(self, name: str, base_branch: str | None = None) -> tuple[int, str]:
        """
        Create a new branch.

        Args:
            name: Branch name to create
            base_branch: Base branch to create from (defaults to current branch)

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Validate branch name
            if not validate_branch_name(name):
                return (1, f"Invalid branch name: {name}")

            # Check if branch already exists
            code, stdout, stderr = run_git_command(
                ['branch', '--list', name],
                cwd=self.repo_root
            )

            if code == 0 and stdout.strip():
                return (1, f"Branch '{name}' already exists")

            # Get base branch
            if not base_branch:
                base_branch = self.get_current_branch()

            # Create the branch
            code, stdout, stderr = run_git_command(
                ['checkout', '-b', name, base_branch],
                cwd=self.repo_root
            )

            if code != 0:
                return (code, f"Failed to create branch: {stderr}")

            # Initialize branch state
            self.config.branch_states[name] = BranchState(
                branch_name=name,
                status=BranchStatus.ACTIVE,
                created_at=self._get_current_timestamp(),
                phase_order=1
            )
            self.config.save_branch_states()

            self.logger.info(f"Created branch '{name}' from '{base_branch}'")
            return (0, f"Created and checked out branch '{name}' from '{base_branch}'")

        except Exception as e:
            error_msg = f"Error creating branch: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)

    def delete_branch(self, branch_name: str, force: bool = False) -> tuple[int, str]:
        """
        Delete a branch.

        Args:
            branch_name: Branch name to delete
            force: If True, force delete even if not merged

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Check if branch is protected
            if self.is_protected_branch(branch_name):
                return (1, f"Cannot delete protected branch '{branch_name}'")

            # Check if branch is current
            current = self.get_current_branch()
            if current == branch_name:
                return (1, f"Cannot delete current branch '{branch_name}'")

            # Delete the branch
            cmd = ['branch', '-D' if force else '-d', branch_name]
            code, _stdout, stderr = run_git_command(cmd, cwd=self.repo_root)

            if code != 0:
                return (code, f"Failed to delete branch: {stderr}")

            # Remove branch state
            if branch_name in self.config.branch_states:
                del self.config.branch_states[branch_name]
                self.config.save_branch_states()

            self.logger.info(f"Deleted branch '{branch_name}'")
            return (0, f"Deleted branch '{branch_name}'")

        except Exception as e:
            error_msg = f"Error deleting branch: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)

    def switch_branch(self, branch_name: str) -> tuple[int, str]:
        """
        Switch to a different branch.

        Args:
            branch_name: Branch name to switch to

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Check if branch exists
            code, stdout, stderr = run_git_command(
                ['branch', '--list', branch_name],
                cwd=self.repo_root
            )

            if code != 0 or not stdout.strip():
                return (1, f"Branch '{branch_name}' does not exist")

            # Switch to branch
            code, stdout, stderr = run_git_command(
                ['checkout', branch_name],
                cwd=self.repo_root
            )

            if code != 0:
                return (code, f"Failed to switch branch: {stderr}")

            self.logger.info(f"Switched to branch '{branch_name}'")
            return (0, f"Switched to branch '{branch_name}'")

        except Exception as e:
            error_msg = f"Error switching branch: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)

    def list_branches(self, include_remote: bool = False) -> tuple[int, str]:
        """
        List all branches.

        Args:
            include_remote: If True, include remote branches

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            cmd = ['branch', '-a'] if include_remote else ['branch']
            code, stdout, stderr = run_git_command(cmd, cwd=self.repo_root)

            if code != 0:
                return (code, f"Failed to list branches: {stderr}")

            branches = [line.strip('* ') for line in stdout.strip().split('\n')]
            current = self.get_current_branch()

            # Mark current branch
            formatted = []
            for branch in branches:
                marker = '*' if branch == current else ' '
                formatted.append(f"{marker} {branch}")

            result = "\n".join(formatted)
            self.logger.info(f"Listed {len(branches)} branches")
            return (0, result)

        except Exception as e:
            error_msg = f"Error listing branches: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)

    def cleanup_failed_branches(self) -> tuple[int, list[str]]:
        """
        Clean up branches that failed to complete workflow.

        Returns:
            Tuple of (count, list of cleaned branch names)
        """
        cleaned = []

        try:
            # Get all local branches
            code, stdout, stderr = run_git_command(
                ['branch', '--format', '%(refname:short)'],
                cwd=self.repo_root
            )

            if code != 0:
                self.logger.error(f"Failed to list branches: {stderr}")
                return (0, cleaned)

            all_branches = stdout.strip().split('\n')

            for branch in all_branches:
                if self.is_protected_branch(branch):
                    continue

                # Check if branch has failed state
                state = self.config.branch_states.get(branch)
                if state and state.status == BranchStatus.FAILED:
                    # Delete the branch
                    code, _msg = self.delete_branch(branch, force=True)
                    if code == 0:
                        cleaned.append(branch)

            self.logger.info(f"Cleaned up {len(cleaned)} failed branches")
            return (len(cleaned), cleaned)

        except Exception as e:
            self.logger.error(f"Error cleaning up failed branches: {e}")
            return (0, cleaned)

    def cleanup_orphaned_branches(self, dry_run: bool = False) -> tuple[int, list[str]]:
        """
        Clean up branches that are not tracked in state.

        Args:
            dry_run: If True, only report without deleting

        Returns:
            Tuple of (count, list of branch names)
        """
        orphaned = []

        try:
            # Get all local branches
            code, stdout, stderr = run_git_command(
                ['branch', '--format', '%(refname:short)'],
                cwd=self.repo_root
            )

            if code != 0:
                self.logger.error(f"Failed to list branches: {stderr}")
                return (0, orphaned)

            all_branches = stdout.strip().split('\n')

            for branch in all_branches:
                if self.is_protected_branch(branch):
                    continue

                # Check if branch is in state
                if branch not in self.config.branch_states:
                    orphaned.append(branch)

            if not dry_run and orphaned:
                for branch in orphaned:
                    code, _msg = self.delete_branch(branch, force=True)

            self.logger.info(f"Found {len(orphaned)} orphaned branches")
            return (len(orphaned), orphaned)

        except Exception as e:
            self.logger.error(f"Error cleaning up orphaned branches: {e}")
            return (0, orphaned)

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()
