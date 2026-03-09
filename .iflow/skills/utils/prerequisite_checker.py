"""Prerequisite Checker - Validates prerequisites before workflow execution.

This module provides functionality for checking and validating that all
prerequisites are met before executing workflows or pipeline stages.
"""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum
import shutil

from .version_check import VersionChecker


class PrerequisiteType(Enum):
    """Types of prerequisites."""
    TOOL_AVAILABLE = "tool_available"
    TOOL_VERSION = "tool_version"
    FILE_EXISTS = "file_exists"
    DIRECTORY_EXISTS = "directory_exists"
    ENVIRONMENT_VARIABLE = "environment_variable"
    CONFIG_VALID = "config_valid"
    DOCUMENT_EXISTS = "document_exists"
    DOCUMENT_VALID = "document_valid"
    DEPENDENCY_AVAILABLE = "dependency_available"
    GIT_REPOSITORY = "git_repository"
    GIT_BRANCH_EXISTS = "git_branch_exists"
    WORKFLOW_STATE_VALID = "workflow_state_valid"
    PERMISSIONS = "permissions"
    DISK_SPACE = "disk_space"
    NETWORK_ACCESS = "network_access"


class PrerequisiteStatus(Enum):
    """Status of a prerequisite check."""
    PENDING = "pending"
    CHECKING = "checking"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


class Prerequisite:
    """Represents a single prerequisite check."""
    
    def __init__(
        self,
        check_id: str,
        name: str,
        prerequisite_type: PrerequisiteType,
        description: str,
        severity: str = "error",
        optional: bool = False
    ):
        """
        Initialize a prerequisite.
        
        Args:
            check_id: Unique identifier for the check
            name: Human-readable name
            prerequisite_type: Type of prerequisite
            description: Description of what is being checked
            severity: Severity level (error, warning, info)
            optional: Whether the check is optional
        """
        self.check_id = check_id
        self.name = name
        self.prerequisite_type = prerequisite_type
        self.description = description
        self.severity = severity
        self.optional = optional
        self.status = PrerequisiteStatus.PENDING
        self.message: Optional[str] = None
        self.details: Optional[Dict[str, Any]] = None
    
    def mark_passed(self, message: Optional[str] = None, details: Optional[Dict] = None):
        """Mark the prerequisite as passed."""
        self.status = PrerequisiteStatus.PASSED
        self.message = message
        self.details = details
    
    def mark_failed(self, message: str, details: Optional[Dict] = None):
        """Mark the prerequisite as failed."""
        self.status = PrerequisiteStatus.FAILED
        self.message = message
        self.details = details
    
    def mark_warning(self, message: str, details: Optional[Dict] = None):
        """Mark the prerequisite as warning."""
        self.status = PrerequisiteStatus.WARNING
        self.message = message
        self.details = details
    
    def mark_skipped(self, message: Optional[str] = None):
        """Mark the prerequisite as skipped."""
        self.status = PrerequisiteStatus.SKIPPED
        self.message = message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prerequisite to dictionary."""
        return {
            "check_id": self.check_id,
            "name": self.name,
            "type": self.prerequisite_type.value,
            "description": self.description,
            "severity": self.severity,
            "optional": self.optional,
            "status": self.status.value,
            "message": self.message,
            "details": self.details
        }


class PrerequisiteChecker:
    """Checks and validates prerequisites for workflows."""
    
    def __init__(self, repo_root: Path):
        """
        Initialize the prerequisite checker.
        
        Args:
            repo_root: Repository root directory
        """
        self.repo_root = repo_root
        self.version_checker = VersionChecker()
        self.prerequisites: List[Prerequisite] = []
        self.checked: Set[str] = set()
    
    def add_prerequisite(self, prerequisite: Prerequisite):
        """
        Add a prerequisite to check.
        
        Args:
            prerequisite: Prerequisite to add
        """
        self.prerequisites.append(prerequisite)
    
    def add_prerequisites(self, prerequisites: List[Prerequisite]):
        """
        Add multiple prerequisites.
        
        Args:
            prerequisites: List of prerequisites to add
        """
        self.prerequisites.extend(prerequisites)
    
    def clear(self):
        """Clear all prerequisites."""
        self.prerequisites.clear()
        self.checked.clear()
    
    def check_tool_available(self, tool_name: str) -> Prerequisite:
        """
        Check if a tool is available on the system.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            Prerequisite with check result
        """
        prerequisite = Prerequisite(
            check_id=f"tool_available_{tool_name}",
            name=f"Tool Available: {tool_name}",
            prerequisite_type=PrerequisiteType.TOOL_AVAILABLE,
            description=f"Check if {tool_name} is installed and available"
        )
        
        path = shutil.which(tool_name)
        if path:
            prerequisite.mark_passed(
                message=f"{tool_name} is available at {path}",
                details={"path": path}
            )
        else:
            prerequisite.mark_failed(
                message=f"{tool_name} is not installed or not in PATH"
            )
        
        return prerequisite
    
    def check_tool_version(
        self,
        tool_name: str,
        min_version: Optional[str] = None,
        max_version: Optional[str] = None
    ) -> Prerequisite:
        """
        Check if a tool meets version requirements.
        
        Args:
            tool_name: Name of the tool
            min_version: Minimum required version
            max_version: Maximum allowed version
            
        Returns:
            Prerequisite with check result
        """
        prerequisite = Prerequisite(
            check_id=f"tool_version_{tool_name}",
            name=f"Tool Version: {tool_name}",
            prerequisite_type=PrerequisiteType.TOOL_VERSION,
            description=f"Check {tool_name} version meets requirements"
        )
        
        try:
            result = subprocess.run(
                [tool_name, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = self.version_checker._parse_version(result.stdout or result.stderr)
                prerequisite.mark_passed(
                    message=f"{tool_name} version: {version}",
                    details={"version": version}
                )
            else:
                prerequisite.mark_failed(
                    message=f"Failed to get {tool_name} version"
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            prerequisite.mark_failed(
                message=f"{tool_name} not found or version check timed out"
            )
        
        return prerequisite
    
    def check_file_exists(self, file_path: Path) -> Prerequisite:
        """
        Check if a file exists.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Prerequisite with check result
        """
        prerequisite = Prerequisite(
            check_id=f"file_exists_{file_path.name}",
            name=f"File Exists: {file_path.name}",
            prerequisite_type=PrerequisiteType.FILE_EXISTS,
            description=f"Check if {file_path} exists"
        )
        
        if file_path.exists():
            if file_path.is_file():
                prerequisite.mark_passed(
                    message=f"File exists: {file_path}",
                    details={"path": str(file_path), "size": file_path.stat().st_size}
                )
            else:
                prerequisite.mark_failed(
                    message=f"Path exists but is not a file: {file_path}"
                )
        else:
            prerequisite.mark_failed(
                message=f"File not found: {file_path}"
            )
        
        return prerequisite
    
    def check_directory_exists(self, dir_path: Path) -> Prerequisite:
        """
        Check if a directory exists.
        
        Args:
            dir_path: Path to the directory
            
        Returns:
            Prerequisite with check result
        """
        prerequisite = Prerequisite(
            check_id=f"dir_exists_{dir_path.name}",
            name=f"Directory Exists: {dir_path.name}",
            prerequisite_type=PrerequisiteType.DIRECTORY_EXISTS,
            description=f"Check if {dir_path} exists and is a directory"
        )
        
        if dir_path.exists():
            if dir_path.is_dir():
                prerequisite.mark_passed(
                    message=f"Directory exists: {dir_path}",
                    details={"path": str(dir_path)}
                )
            else:
                prerequisite.mark_failed(
                    message=f"Path exists but is not a directory: {dir_path}"
                )
        else:
            prerequisite.mark_failed(
                message=f"Directory not found: {dir_path}"
            )
        
        return prerequisite
    
    def check_environment_variable(
        self,
        var_name: str,
        required: bool = True
    ) -> Prerequisite:
        """
        Check if an environment variable is set.
        
        Args:
            var_name: Name of the environment variable
            required: Whether the variable is required
            
        Returns:
            Prerequisite with check result
        """
        prerequisite = Prerequisite(
            check_id=f"env_var_{var_name}",
            name=f"Environment Variable: {var_name}",
            prerequisite_type=PrerequisiteType.ENVIRONMENT_VARIABLE,
            description=f"Check if {var_name} environment variable is set",
            optional=not required
        )
        
        value = os.environ.get(var_name)
        if value:
            prerequisite.mark_passed(
                message=f"{var_name} is set",
                details={"variable": var_name, "value": "***"}
            )
        else:
            if required:
                prerequisite.mark_failed(
                    message=f"{var_name} environment variable is not set"
                )
            else:
                prerequisite.mark_warning(
                    message=f"{var_name} environment variable is not set (optional)"
                )
        
        return prerequisite
    
    def check_git_repository(self) -> Prerequisite:
        """
        Check if current directory is a git repository.
        
        Returns:
            Prerequisite with check result
        """
        prerequisite = Prerequisite(
            check_id="git_repository",
            name="Git Repository",
            prerequisite_type=PrerequisiteType.GIT_REPOSITORY,
            description="Check if current directory is a git repository"
        )
        
        git_dir = self.repo_root / ".git"
        if git_dir.exists():
            prerequisite.mark_passed(
                message="Git repository detected",
                details={"path": str(self.repo_root)}
            )
        else:
            prerequisite.mark_failed(
                message="Not a git repository"
            )
        
        return prerequisite
    
    def check_git_branch_exists(self, branch_name: str) -> Prerequisite:
        """
        Check if a git branch exists.
        
        Args:
            branch_name: Name of the branch
            
        Returns:
            Prerequisite with check result
        """
        prerequisite = Prerequisite(
            check_id=f"git_branch_{branch_name}",
            name=f"Git Branch: {branch_name}",
            prerequisite_type=PrerequisiteType.GIT_BRANCH_EXISTS,
            description=f"Check if git branch {branch_name} exists"
        )
        
        try:
            result = subprocess.run(
                ["git", "branch", "--list", branch_name],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                timeout=10
            )
            
            if result.returncode == 0 and branch_name in result.stdout:
                prerequisite.mark_passed(
                    message=f"Branch {branch_name} exists"
                )
            else:
                prerequisite.mark_failed(
                    message=f"Branch {branch_name} does not exist"
                )
        except subprocess.TimeoutExpired:
            prerequisite.mark_failed(
                message="Git branch check timed out"
            )
        
        return prerequisite
    
    def check_disk_space(self, min_space_mb: int = 100) -> Prerequisite:
        """
        Check if sufficient disk space is available.
        
        Args:
            min_space_mb: Minimum required disk space in MB
            
        Returns:
            Prerequisite with check result
        """
        prerequisite = Prerequisite(
            check_id="disk_space",
            name="Disk Space",
            prerequisite_type=PrerequisiteType.DISK_SPACE,
            description=f"Check if at least {min_space_mb}MB disk space is available"
        )
        
        try:
            usage = shutil.disk_usage(self.repo_root)
            available_mb = usage.free / (1024 * 1024)
            
            if available_mb >= min_space_mb:
                prerequisite.mark_passed(
                    message=f"Sufficient disk space: {available_mb:.0f}MB available",
                    details={"available_mb": available_mb, "required_mb": min_space_mb}
                )
            else:
                prerequisite.mark_failed(
                    message=f"Insufficient disk space: {available_mb:.0f}MB available, {min_space_mb}MB required"
                )
        except Exception as e:
            prerequisite.mark_failed(
                message=f"Failed to check disk space: {str(e)}"
            )
        
        return prerequisite
    
    def check_permissions(self, file_path: Path, required_permission: str = "read") -> Prerequisite:
        """
        Check file permissions.
        
        Args:
            file_path: Path to check
            required_permission: Type of permission required (read, write, execute)
            
        Returns:
            Prerequisite with check result
        """
        prerequisite = Prerequisite(
            check_id=f"permissions_{file_path.name}",
            name=f"Permissions: {file_path.name}",
            prerequisite_type=PrerequisiteType.PERMISSIONS,
            description=f"Check if {required_permission} permission on {file_path}"
        )
        
        try:
            if required_permission == "read":
                if os.access(file_path, os.R_OK):
                    prerequisite.mark_passed(message=f"Read permission granted")
                else:
                    prerequisite.mark_failed(message=f"Read permission denied")
            elif required_permission == "write":
                if os.access(file_path, os.W_OK):
                    prerequisite.mark_passed(message=f"Write permission granted")
                else:
                    prerequisite.mark_failed(message=f"Write permission denied")
            elif required_permission == "execute":
                if os.access(file_path, os.X_OK):
                    prerequisite.mark_passed(message=f"Execute permission granted")
                else:
                    prerequisite.mark_failed(message=f"Execute permission denied")
        except Exception as e:
            prerequisite.mark_failed(message=f"Failed to check permissions: {str(e)}")
        
        return prerequisite
    
    def check_all(self) -> Tuple[bool, List[Prerequisite]]:
        """
        Check all prerequisites.
        
        Returns:
            Tuple of (all_passed, list_of_prerequisites)
        """
        results = []
        
        for prereq in self.prerequisites:
            if prereq.check_id not in self.checked:
                prereq.status = PrerequisiteStatus.CHECKING
                
                # Execute the appropriate check
                if prereq.prerequisite_type == PrerequisiteType.TOOL_AVAILABLE:
                    tool_name = prereq.name.split(":")[1].strip()
                    result = self.check_tool_available(tool_name)
                    prereq.status = result.status
                    prereq.message = result.message
                    prereq.details = result.details
                
                self.checked.add(prereq.check_id)
            
            results.append(prereq)
        
        # Determine if all required checks passed
        required_passed = all(
            pr.status in [PrerequisiteStatus.PASSED, PrerequisiteStatus.SKIPPED]
            for pr in results
            if not pr.optional and pr.severity == "error"
        )
        
        return required_passed, results
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of prerequisite checks.
        
        Returns:
            Dictionary with summary statistics
        """
        total = len(self.prerequisites)
        passed = sum(1 for pr in self.prerequisites if pr.status == PrerequisiteStatus.PASSED)
        failed = sum(1 for pr in self.prerequisites if pr.status == PrerequisiteStatus.FAILED)
        warnings = sum(1 for pr in self.prerequisites if pr.status == PrerequisiteStatus.WARNING)
        skipped = sum(1 for pr in self.prerequisites if pr.status == PrerequisiteStatus.SKIPPED)
        
        required_failed = sum(
            1 for pr in self.prerequisites
            if pr.status == PrerequisiteStatus.FAILED
            and not pr.optional
            and pr.severity == "error"
        )
        
        return {
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "skipped": skipped,
            "all_required_passed": required_failed == 0,
            "success_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%"
        }


def create_prerequisite_checker(repo_root: Path) -> PrerequisiteChecker:
    """Create a prerequisite checker instance."""
    return PrerequisiteChecker(repo_root)


def validate_workflow_prerequisites(
    repo_root: Path,
    required_tools: Optional[List[str]] = None,
    required_env_vars: Optional[List[str]] = None,
    min_disk_space_mb: int = 100
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate common workflow prerequisites.
    
    Args:
        repo_root: Repository root directory
        required_tools: List of required tools
        required_env_vars: List of required environment variables
        min_disk_space_mb: Minimum required disk space
        
    Returns:
        Tuple of (all_passed, summary_dict)
    """
    checker = create_prerequisite_checker(repo_root)
    
    # Add standard checks
    checker.add_prerequisite(checker.check_git_repository())
    checker.add_prerequisite(checker.check_disk_space(min_disk_space_mb))
    
    # Add tool checks
    if required_tools:
        for tool in required_tools:
            checker.add_prerequisite(checker.check_tool_available(tool))
    
    # Add environment variable checks
    if required_env_vars:
        for var in required_env_vars:
            checker.add_prerequisite(checker.check_environment_variable(var, required=True))
    
    # Run all checks
    all_passed, results = checker.check_all()
    
    return all_passed, {
        "summary": checker.get_summary(),
        "prerequisites": [pr.to_dict() for pr in results]
    }