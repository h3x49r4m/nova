#!/usr/bin/env python3
"""
Git-Flow Merge Module
Handles merge operations, conflict resolution, and dependency management.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from utils import run_git_command

if TYPE_CHECKING:
    from .git_flow_branches import GitFlowBranches
    from .git_flow_config import GitFlowConfig


class GitFlowMerge:
    """Manages Git-Flow merge operations and dependency resolution."""

    def __init__(self, config: GitFlowConfig, branches: GitFlowBranches):
        """
        Initialize merge manager.

        Args:
            config: GitFlowConfig instance
            branches: GitFlowBranches instance
        """
        self.config = config
        self.branches = branches
        self.logger = config.logger
        self.repo_root = config.repo_root

    def merge_branch(self, branch_name: str, target_branch: str | None = None) -> tuple[int, str]:
        """
        Merge a branch into its target.

        Args:
            branch_name: Branch to merge
            target_branch: Target branch (defaults to protected branch)

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Check if branch exists
            if branch_name not in self.config.branch_states:
                return (1, f"Branch '{branch_name}' not found in workflow state")

            # Get target branch
            if not target_branch:
                # Find appropriate protected branch
                target_branch = self._get_target_branch(branch_name)

            # Validate dependencies
            valid, msg = self._validate_dependencies_for_merge(branch_name)
            if not valid:
                return (1, f"Dependency validation failed: {msg}")

            # Switch to target branch
            code, msg = self.branches.switch_branch(target_branch)
            if code != 0:
                return (code, f"Failed to switch to target branch: {msg}")

            # Get merge strategy
            strategy = self.config.get_config_value('merge', 'strategy', default='rebase-merge')

            # Perform merge
            if strategy == 'rebase-merge':
                code, msg = self._rebase_merge(branch_name, target_branch)
            else:
                code, msg = self._fast_forward_merge(branch_name, target_branch)

            if code != 0:
                return (code, msg)

            # Update branch state
            branch_state = self.config.branch_states.get(branch_name)
            if branch_state:
                branch_state.merged = True
                branch_state.merged_at = datetime.now().isoformat()

                # Get merge commit
                code, stdout, _stderr = run_git_command(
                    ['rev-parse', 'HEAD'],
                    cwd=self.repo_root
                )
                if code == 0:
                    branch_state.merge_commit = stdout.strip()

                self.config.save_branch_states()

            # Delete branch if configured
            delete_after = self.config.get_config_value(
                'merge', 'delete_branch_after_merge', default=True
            )
            if delete_after:
                self.branches.delete_branch(branch_name, force=False)

            message = f"Merged '{branch_name}' into '{target_branch}'"
            self.logger.info(message)
            return (0, message)

        except Exception as e:
            error_msg = f"Error merging branch: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)

    def _rebase_merge(self, source: str, target: str) -> tuple[int, str]:
        """
        Perform a rebase merge.

        Args:
            source: Source branch
            target: Target branch

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Pull latest changes
            code, stdout, stderr = run_git_command(
                ['pull', '--rebase', 'origin', target],
                cwd=self.repo_root
            )
            if code != 0:
                return (code, f"Failed to pull latest changes: {stderr}")

            # Merge source branch
            code, _stdout, stderr = run_git_command(
                ['merge', '--no-ff', source, '-m', f"Merge branch '{source}' into {target}"],
                cwd=self.repo_root
            )

            if code != 0:
                # Check for conflicts
                has_conflicts, conflicts = self.check_for_conflicts()
                if has_conflicts:
                    return (1, f"Merge conflicts detected:\n{chr(10).join(conflicts)}")
                return (code, f"Merge failed: {stderr}")

            return (0, "Rebase merge completed successfully")

        except Exception as e:
            return (1, f"Rebase merge error: {e}")

    def _fast_forward_merge(self, source: str, target: str) -> tuple[int, str]:
        """
        Perform a fast-forward merge.

        Args:
            source: Source branch
            target: Target branch

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Pull latest changes
            code, stdout, stderr = run_git_command(
                ['pull', 'origin', target],
                cwd=self.repo_root
            )
            if code != 0:
                return (code, f"Failed to pull latest changes: {stderr}")

            # Merge source branch
            code, _stdout, stderr = run_git_command(
                ['merge', '--ff-only', source],
                cwd=self.repo_root
            )

            if code != 0:
                return (code, f"Fast-forward merge failed: {stderr}")

            return (0, "Fast-forward merge completed successfully")

        except Exception as e:
            return (1, f"Fast-forward merge error: {e}")

    def _get_target_branch(self, branch_name: str) -> str:
        """
        Get the target branch for a given branch.

        Args:
            branch_name: Source branch name

        Returns:
            Target branch name
        """
        # Default to main branch
        return 'main'

    def check_for_conflicts(self) -> tuple[bool, list[str]]:
        """
        Check for merge conflicts in the working directory.

        Returns:
            Tuple of (has_conflicts, list of conflicted files)
        """
        try:
            code, stdout, _stderr = run_git_command(
                ['status', '--porcelain'],
                cwd=self.repo_root
            )

            if code != 0:
                return (False, [])

            conflicts = []
            for line in stdout.strip().split('\n'):
                if line.startswith('UU') or line.startswith('AA') or line.startswith('DD'):
                    # Extract file name
                    filename = line[3:].strip()
                    conflicts.append(filename)

            return (len(conflicts) > 0, conflicts)

        except Exception as e:
            self.logger.error(f"Error checking for conflicts: {e}")
            return (False, [])

    def abort_merge_operation(self) -> tuple[int, str]:
        """
        Abort the current merge operation.

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Check if merge is in progress
            code, stdout, stderr = run_git_command(
                ['status', '--porcelain'],
                cwd=self.repo_root
            )

            if code != 0 or 'MERGE' not in stdout:
                return (1, "No merge in progress")

            # Abort merge
            code, stdout, stderr = run_git_command(
                ['merge', '--abort'],
                cwd=self.repo_root
            )

            if code != 0:
                return (code, f"Failed to abort merge: {stderr}")

            self.logger.info("Merge operation aborted")
            return (0, "Merge operation aborted successfully")

        except Exception as e:
            error_msg = f"Error aborting merge: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)

    def resolve_conflicts_with_strategy(self, strategy: str = 'theirs') -> tuple[int, str]:
        """
        Resolve conflicts using a specific strategy.

        Args:
            strategy: Conflict resolution strategy ('theirs', 'ours', 'manual')

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            has_conflicts, conflicts = self.check_for_conflicts()
            if not has_conflicts:
                return (0, "No conflicts to resolve")

            if strategy == 'manual':
                return (0, f"Please resolve {len(conflicts)} conflicts manually")

            # Auto-resolve conflicts
            for filename in conflicts:
                if strategy == 'theirs':
                    code, stdout, stderr = run_git_command(
                        ['checkout', '--theirs', filename],
                        cwd=self.repo_root
                    )
                elif strategy == 'ours':
                    code, stdout, stderr = run_git_command(
                        ['checkout', '--ours', filename],
                        cwd=self.repo_root
                    )

                if code != 0:
                    return (code, f"Failed to resolve conflict in '{filename}': {stderr}")

                # Stage the resolved file
                code, _stdout, stderr = run_git_command(
                    ['add', filename],
                    cwd=self.repo_root
                )
                if code != 0:
                    return (code, f"Failed to stage '{filename}': {stderr}")

            message = f"Resolved {len(conflicts)} conflicts using '{strategy}' strategy"
            self.logger.info(message)
            return (0, message)

        except Exception as e:
            error_msg = f"Error resolving conflicts: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)

    def _validate_dependencies_for_merge(self, branch_name: str) -> tuple[bool, str]:
        """
        Validate that all dependencies are merged.

        Args:
            branch_name: Branch to validate

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            require_deps = self.config.get_config_value(
                'merge', 'require_dependencies_merged', default=True
            )

            if not require_deps:
                return (True, "")

            branch_state = self.config.branch_states.get(branch_name)
            if not branch_state or not branch_state.dependencies:
                return (True, "")

            # Check each dependency
            for dep_branch in branch_state.dependencies:
                dep_state = self.config.branch_states.get(dep_branch)
                if not dep_state or not dep_state.merged:
                    return (False, f"Dependency '{dep_branch}' is not merged")

            return (True, "")

        except Exception as e:
            self.logger.error(f"Error validating dependencies: {e}")
            return (False, f"Dependency validation error: {e}")

    def _has_circular_dependency(self, branch_name: str, visited: set[str] | None = None) -> bool:
        """
        Check if adding a dependency would create a circular dependency.

        Args:
            branch_name: Branch to check
            visited: Set of already visited branches

        Returns:
            True if circular dependency detected
        """
        if visited is None:
            visited = set()

        if branch_name in visited:
            return True

        visited.add(branch_name)

        branch_state = self.config.branch_states.get(branch_name)
        if not branch_state:
            return False

        for dep in branch_state.dependencies:
            if self._has_circular_dependency(dep, visited.copy()):
                return True

        return False

    def add_dependency(self, branch_name: str, dependency: str) -> tuple[int, str]:
        """
        Add a dependency to a branch.

        Args:
            branch_name: Branch to add dependency to
            dependency: Branch to depend on

        Returns:
            Tuple of (exit_code, message)
        """
        try:
            # Check if branches exist
            if branch_name not in self.config.branch_states:
                return (1, f"Branch '{branch_name}' not found")

            if dependency not in self.config.branch_states:
                return (1, f"Dependency branch '{dependency}' not found")

            # Check for circular dependency
            if self._has_circular_dependency(branch_name):
                return (1, "Adding this dependency would create a circular dependency")

            # Add dependency
            branch_state = self.config.branch_states[branch_name]
            if dependency not in branch_state.dependencies:
                branch_state.dependencies.append(dependency)
                self.config.save_branch_states()

            message = f"Added dependency '{dependency}' to '{branch_name}'"
            self.logger.info(message)
            return (0, message)

        except Exception as e:
            error_msg = f"Error adding dependency: {e}"
            self.logger.error(error_msg)
            return (1, error_msg)

    def detect_deadlocks(self) -> tuple[bool, list[dict]]:
        """
        Detect deadlock situations in the dependency graph.

        Returns:
            Tuple of (has_deadlocks, list of deadlock info)
        """
        deadlocks = []

        for branch_name in self.config.branch_states:
            if self._has_circular_dependency(branch_name):
                deadlocks.append({
                    'branch': branch_name,
                    'type': 'circular_dependency'
                })

        return (len(deadlocks) > 0, deadlocks)

    def get_dependency_report(self) -> dict:
        """
        Generate a dependency report for all branches.

        Returns:
            Dictionary with dependency information
        """
        report = {
            'total_branches': len(self.config.branch_states),
            'branches_with_dependencies': 0,
            'dependency_graph': {},
            'deadlocks': []
        }

        for branch_name, state in self.config.branch_states.items():
            if state.dependencies:
                report['branches_with_dependencies'] += 1
                report['dependency_graph'][branch_name] = state.dependencies

        # Check for deadlocks
        has_deadlocks, deadlocks = self.detect_deadlocks()
        if has_deadlocks:
            report['deadlocks'] = deadlocks

        return report
