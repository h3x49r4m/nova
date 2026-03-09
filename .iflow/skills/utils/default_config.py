"""Default Configuration - Centralized default configuration definitions.

This module provides centralized default configuration values for all
iFlow CLI Skills components.
"""

from pathlib import Path
from typing import Any, Dict

from .constants import (
    Timeouts,
    RetryPolicy,
    GitBranches,
    CoverageThresholds,
    FileSizeLimits,
    CachePolicy,
    BackupConstants,
    SecretPatterns,
    CommitTypes,
    LoggingConstants
)


class DefaultConfig:
    """Centralized default configuration values."""
    
    # Repository configuration
    REPO_ROOT = Path.cwd()
    SKILLS_DIR = REPO_ROOT / ".iflow" / "skills"
    SHARED_STATE_DIR = REPO_ROOT / ".iflow" / "skills" / ".shared-state"
    BACKUP_DIR = REPO_ROOT / ".iflow" / "skills" / "backups"
    LOG_DIR = REPO_ROOT / ".iflow" / "logs"
    SCHEMAS_DIR = REPO_ROOT / ".iflow" / "schemas"
    PROFILES_DIR = REPO_ROOT / ".iflow" / "profiles"
    
    # File extensions
    PYTHON_EXT = ".py"
    JSON_EXT = ".json"
    MARKDOWN_EXT = ".md"
    YAML_EXT = ".yaml"
    YML_EXT = ".yml"
    
    # Git configuration
    GIT_DEFAULT_REMOTE = "origin"
    GIT_DEFAULT_BRANCH = GitBranches.MAIN.value
    GIT_PROTECTED_BRANCHES = [
        GitBranches.MAIN.value,
        GitBranches.MASTER.value,
        GitBranches.PRODUCTION.value
    ]
    
    # Workflow configuration
    WORKFLOW_DEFAULT_PHASES = [
        {
            "name": "Requirements Gathering",
            "role": "Client",
            "order": 1,
            "required": True
        },
        {
            "name": "Architecture Design",
            "role": "Tech Lead",
            "order": 2,
            "required": True
        },
        {
            "name": "Implementation",
            "role": "Software Engineer",
            "order": 3,
            "required": True
        },
        {
            "name": "Testing",
            "role": "QA Engineer",
            "order": 4,
            "required": True
        },
        {
            "name": "Design",
            "role": "UI/UX Designer",
            "order": 5,
            "required": False
        },
        {
            "name": "Documentation",
            "role": "Documentation Specialist",
            "order": 6,
            "required": False
        },
        {
            "name": "Security Review",
            "role": "Security Engineer",
            "order": 7,
            "required": False
        },
        {
            "name": "Deployment",
            "role": "DevOps Engineer",
            "order": 8,
            "required": True
        }
    ]
    
    # Document templates
    DOCUMENT_TEMPLATES = [
        "project-spec.template.md",
        "design-spec.template.md",
        "architecture-spec.template.md",
        "implementation-plan.template.md",
        "implementation.template.md",
        "test-plan.template.md",
        "test-results.template.md",
        "quality-report.template.md",
        "security-report.template.md",
        "deployment-status.template.md",
        "api-docs.template.md",
        "user-guide.template.md",
        "changelog.template.md",
        "pipeline-status.template.md"
    ]
    
    # State documents
    STATE_DOCUMENTS = [
        "project-spec.md",
        "design-spec.md",
        "architecture-spec.md",
        "implementation-plan.md",
        "implementation.md",
        "test-plan.md",
        "test-results.md",
        "quality-report.md",
        "security-report.md",
        "deployment-status.md",
        "api-docs.md",
        "user-guide.md",
        "changelog.md",
        "pipeline-status.md"
    ]
    
    # Roles
    ROLES = [
        "Client",
        "Product Manager",
        "Tech Lead",
        "Software Engineer",
        "Testing Engineer",
        "QA Engineer",
        "Security Engineer",
        "DevOps Engineer",
        "Documentation Specialist",
        "UI/UX Designer",
        "Project Manager"
    ]
    
    # Pipeline configurations
    TEAM_PIPELINES = {
        "team-pipeline-new-project": {
            "name": "New Project Pipeline",
            "description": "Creates a new project from scratch",
            "stages": [
                {
                    "name": "Requirements Gathering",
                    "skills": ["client"],
                    "required": True
                },
                {
                    "name": "Architecture Design",
                    "skills": ["tech-lead"],
                    "required": True
                },
                {
                    "name": "Implementation",
                    "skills": ["software-engineer"],
                    "required": True
                },
                {
                    "name": "Testing",
                    "skills": ["testing-engineer", "qa-engineer"],
                    "required": True
                },
                {
                    "name": "Documentation",
                    "skills": ["documentation-specialist"],
                    "required": False
                },
                {
                    "name": "Deployment",
                    "skills": ["devops-engineer"],
                    "required": True
                }
            ]
        },
        "team-pipeline-new-feature": {
            "name": "New Feature Pipeline",
            "description": "Adds a new feature to existing project",
            "stages": [
                {
                    "name": "Feature Planning",
                    "skills": ["product-manager"],
                    "required": True
                },
                {
                    "name": "Design",
                    "skills": ["ui-ux-designer", "tech-lead"],
                    "required": False
                },
                {
                    "name": "Implementation",
                    "skills": ["software-engineer"],
                    "required": True
                },
                {
                    "name": "Testing",
                    "skills": ["testing-engineer", "qa-engineer"],
                    "required": True
                },
                {
                    "name": "Code Review",
                    "skills": ["team-pipeline-auto-review"],
                    "required": True
                },
                {
                    "name": "Documentation",
                    "skills": ["documentation-specialist"],
                    "required": False
                }
            ]
        },
        "team-pipeline-fix-bug": {
            "name": "Fix Bug Pipeline",
            "description": "Fixes a bug in existing code",
            "stages": [
                {
                    "name": "Bug Analysis",
                    "skills": ["testing-engineer", "qa-engineer"],
                    "required": True
                },
                {
                    "name": "Fix Implementation",
                    "skills": ["software-engineer"],
                    "required": True
                },
                {
                    "name": "Testing",
                    "skills": ["testing-engineer", "qa-engineer"],
                    "required": True
                },
                {
                    "name": "Verification",
                    "skills": ["qa-engineer"],
                    "required": True
                }
            ]
        },
        "team-pipeline-auto-review": {
            "name": "Auto Review Pipeline",
            "description": "Automated code review pipeline",
            "stages": [
                {
                    "name": "Code Analysis",
                    "skills": ["team-pipeline-auto-review"],
                    "required": True
                },
                {
                    "name": "Quality Checks",
                    "skills": ["team-pipeline-auto-review"],
                    "required": True
                },
                {
                    "name": "Security Scan",
                    "skills": ["security-engineer"],
                    "required": True
                }
            ]
        }
    }
    
    # Quality gates
    QUALITY_GATES = {
        "test_coverage": {
            "enabled": True,
            "min_lines": CoverageThresholds.LINES.value,
            "min_branches": CoverageThresholds.BRANCHES.value,
            "min_functions": CoverageThresholds.FUNCTIONS.value
        },
        "bug_severity": {
            "enabled": True,
            "max_allowed_critical": 0,
            "max_allowed_high": 0,
            "max_allowed_medium": 5
        },
        "security_scan": {
            "enabled": True,
            "max_allowed_critical": 0,
            "max_allowed_high": 0
        },
        "documentation": {
            "enabled": True,
            "min_coverage": 80.0
        },
        "lint_errors": {
            "enabled": True,
            "max_allowed": 10
        },
        "regression_tests": {
            "enabled": True,
            "min_pass_rate": 95.0
        }
    }
    
    # Review tools
    REVIEW_TOOLS = {
        "sonarqube": {
            "enabled": False,
            "url": "",
            "api_key": "",
            "timeout": Timeouts.TEST_DEFAULT.value
        },
        "snyk": {
            "enabled": False,
            "api_key": "",
            "organization": "",
            "timeout": Timeouts.TEST_DEFAULT.value
        },
        "eslint": {
            "enabled": True,
            "config_file": ".eslintrc.json",
            "timeout": Timeouts.TEST_DEFAULT.value
        },
        "pylint": {
            "enabled": True,
            "config_file": ".pylintrc",
            "timeout": Timeouts.TEST_DEFAULT.value
        }
    }
    
    # Coverage thresholds
    COVERAGE_THRESHOLDS = {
        "lines": CoverageThresholds.LINES.value,
        "branches": CoverageThresholds.BRANCHES.value,
        "functions": CoverageThresholds.FUNCTIONS.value,
        "statements": CoverageThresholds.STATEMENTS.value
    }
    
    # Commit types
    COMMIT_TYPES = {ct.value: ct.value.title() for ct in CommitTypes}
    
    # Secret patterns
    SECRET_PATTERNS = [pattern.value for pattern in SecretPatterns]
    
    # File size limits
    FILE_SIZE_LIMITS = {
        "max_diff_size": FileSizeLimits.MAX_DIFF_SIZE.value,
        "max_file_read": FileSizeLimits.MAX_FILE_READ.value,
        "max_log_size": FileSizeLimits.MAX_LOG_SIZE.value
    }
    
    # Backup configuration
    BACKUP_CONFIG = {
        "max_backups_per_file": BackupConstants.MAX_BACKUPS_PER_FILE.value,
        "backup_retention_days": BackupConstants.BACKUP_RETENTION_DAYS.value,
        "max_backup_size_mb": BackupConstants.MAX_BACKUP_SIZE_MB.value,
        "compression_threshold_mb": BackupConstants.COMPRESSION_THRESHOLD_MB.value
    }
    
    # Cache configuration
    CACHE_CONFIG = {
        "default_ttl": CachePolicy.DEFAULT_TTL.value,
        "max_size": CachePolicy.MAX_SIZE.value
    }
    
    # Logging configuration
    LOGGING_CONFIG = {
        "level": "INFO",
        "format": "json",
        "max_file_size_mb": LoggingConstants.LOG_MAX_SIZE_MB.value,
        "backup_count": 5,
        "log_retention_days": LoggingConstants.LOG_RETENTION_DAYS.value
    }
    
    @classmethod
    def get_git_flow_config(cls) -> Dict[str, Any]:
        """Get default git-flow configuration."""
        return {
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
                "protected_branches": cls.GIT_PROTECTED_BRANCHES
            }
        }
    
    @classmethod
    def get_git_manage_config(cls) -> Dict[str, Any]:
        """Get default git-manage configuration."""
        return {
            "pre_commit_checks": True,
            "run_tests": True,
            "run_architecture_check": True,
            "run_tdd_check": True,
            "check_coverage": True,
            "detect_secrets": True,
            "branch_protection": True,
            "protected_branches": cls.GIT_PROTECTED_BRANCHES,
            "coverage_threshold": cls.COVERAGE_THRESHOLDS["lines"],
            "branch_coverage_threshold": cls.COVERAGE_THRESHOLDS["branches"],
            "coverage_thresholds": cls.COVERAGE_THRESHOLDS,
            "commit_types": cls.COMMIT_TYPES,
            "secret_patterns": cls.SECRET_PATTERNS
        }
    
    @classmethod
    def get_pipeline_config(cls) -> Dict[str, Any]:
        """Get default pipeline configuration."""
        return {
            "max_stages": 10,
            "max_skills": 20,
            "timeout": Timeouts.TEST_DEFAULT.value,
            "retry_policy": {
                "max_attempts": RetryPolicy.MAX_ATTEMPTS.value,
                "initial_delay": RetryPolicy.INITIAL_DELAY.value,
                "max_delay": RetryPolicy.MAX_DELAY.value,
                "backoff_factor": RetryPolicy.BACKOFF_FACTOR.value
            },
            "quality_gates": cls.QUALITY_GATES,
            "review_tools": cls.REVIEW_TOOLS
        }
    
    @classmethod
    def get_all_defaults(cls) -> Dict[str, Any]:
        """Get all default configurations."""
        return {
            "git_flow": cls.get_git_flow_config(),
            "git_manage": cls.get_git_manage_config(),
            "pipeline": cls.get_pipeline_config(),
            "quality_gates": cls.QUALITY_GATES,
            "review_tools": cls.REVIEW_TOOLS,
            "coverage_thresholds": cls.COVERAGE_THRESHOLDS,
            "commit_types": cls.COMMIT_TYPES,
            "secret_patterns": cls.SECRET_PATTERNS,
            "file_size_limits": cls.FILE_SIZE_LIMITS,
            "backup_config": cls.BACKUP_CONFIG,
            "cache_config": cls.CACHE_CONFIG,
            "logging_config": cls.LOGGING_CONFIG
        }


def get_default_config(component: str) -> Dict[str, Any]:
    """
    Get default configuration for a specific component.
    
    Args:
        component: Component name (git_flow, git_manage, pipeline, etc.)
        
    Returns:
        Default configuration dictionary
    """
    method_map = {
        "git_flow": DefaultConfig.get_git_flow_config,
        "git_manage": DefaultConfig.get_git_manage_config,
        "pipeline": DefaultConfig.get_pipeline_config,
        "all": DefaultConfig.get_all_defaults
    }
    
    method = method_map.get(component)
    if method:
        return method()
    
    return {}


def merge_with_defaults(
    user_config: Dict[str, Any],
    component: str
) -> Dict[str, Any]:
    """
    Merge user configuration with defaults.
    
    Args:
        user_config: User-provided configuration
        component: Component name
        
    Returns:
        Merged configuration
    """
    defaults = get_default_config(component)
    
    def deep_merge(base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    return deep_merge(defaults, user_config)