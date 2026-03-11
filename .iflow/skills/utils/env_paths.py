#!/usr/bin/env python3
"""
Environment Paths Configuration
Centralized path management using environment variables with fallback defaults.
"""

import os
from pathlib import Path
from typing import Optional

from .structured_logger import StructuredLogger, LogFormat

# Module-level logger for static methods
_logger = StructuredLogger(
    name="env_paths",
    log_dir=Path.cwd() / ".iflow" / "logs",
    log_format=LogFormat.JSON
)


class EnvPaths:
    """Environment-based path configuration with defaults."""

    # Environment variable names
    ENV_IFLOW_ROOT = "IFLOW_ROOT"
    ENV_SKILLS_DIR = "IFLOW_SKILLS_DIR"
    ENV_SHARED_STATE_DIR = "IFLOW_SHARED_STATE_DIR"
    ENV_BACKUP_DIR = "IFLOW_BACKUP_DIR"
    ENV_LOG_DIR = "IFLOW_LOG_DIR"
    ENV_SCHEMA_DIR = "IFLOW_SCHEMA_DIR"
    ENV_CONFIG_DIR = "IFLOW_CONFIG_DIR"

    # Default paths
    DEFAULT_IFLOW_ROOT = ".iflow"
    DEFAULT_SKILLS_DIR = ".iflow/skills"
    DEFAULT_SHARED_STATE_DIR = ".iflow/skills/.shared-state"
    DEFAULT_BACKUP_DIR = ".iflow/skills/backups"
    DEFAULT_LOG_DIR = ".iflow/logs"
    DEFAULT_SCHEMA_DIR = ".iflow/schemas"
    DEFAULT_CONFIG_DIR = ".iflow/skills"

    @staticmethod
    def get_root() -> Path:
        """Get the iFlow root directory."""
        root = os.environ.get(EnvPaths.ENV_IFLOW_ROOT, EnvPaths.DEFAULT_IFLOW_ROOT)
        return Path(root).resolve()

    @staticmethod
    def get_skills_dir() -> Path:
        """Get the skills directory."""
        skills_dir = os.environ.get(
            EnvPaths.ENV_SKILLS_DIR,
            EnvPaths.DEFAULT_SKILLS_DIR
        )
        return Path(skills_dir).resolve()

    @staticmethod
    def get_shared_state_dir() -> Path:
        """Get the shared state directory."""
        shared_state_dir = os.environ.get(
            EnvPaths.ENV_SHARED_STATE_DIR,
            EnvPaths.DEFAULT_SHARED_STATE_DIR
        )
        return Path(shared_state_dir).resolve()

    @staticmethod
    def get_backup_dir() -> Path:
        """Get the backup directory."""
        backup_dir = os.environ.get(
            EnvPaths.ENV_BACKUP_DIR,
            EnvPaths.DEFAULT_BACKUP_DIR
        )
        return Path(backup_dir).resolve()

    @staticmethod
    def get_log_dir() -> Path:
        """Get the log directory."""
        log_dir = os.environ.get(
            EnvPaths.ENV_LOG_DIR,
            EnvPaths.DEFAULT_LOG_DIR
        )
        return Path(log_dir).resolve()

    @staticmethod
    def get_schema_dir() -> Path:
        """Get the schema directory."""
        schema_dir = os.environ.get(
            EnvPaths.ENV_SCHEMA_DIR,
            EnvPaths.DEFAULT_SCHEMA_DIR
        )
        return Path(schema_dir).resolve()

    @staticmethod
    def get_config_dir() -> Path:
        """Get the config directory."""
        config_dir = os.environ.get(
            EnvPaths.ENV_CONFIG_DIR,
            EnvPaths.DEFAULT_CONFIG_DIR
        )
        return Path(config_dir).resolve()

    @staticmethod
    def get_skill_dir(skill_name: str) -> Path:
        """
        Get the directory for a specific skill.

        Args:
            skill_name: Name of the skill

        Returns:
            Path to the skill directory
        """
        return EnvPaths.get_skills_dir() / skill_name

    @staticmethod
    def get_skill_config(skill_name: str) -> Path:
        """
        Get the config file for a specific skill.

        Args:
            skill_name: Name of the skill

        Returns:
            Path to the skill config file
        """
        return EnvPaths.get_skill_dir(skill_name) / "config.json"

    @staticmethod
    def get_git_manage_path() -> Path:
        """Get the path to git-manage script."""
        return EnvPaths.get_skills_dir() / "git-manage" / "git-manage.py"

    @staticmethod
    def get_git_flow_path() -> Path:
        """Get the path to git-flow script."""
        return EnvPaths.get_skills_dir() / "git-flow" / "git-flow.py"

    @staticmethod
    def get_utils_dir() -> Path:
        """Get the utils directory."""
        return EnvPaths.get_skills_dir() / "utils"

    @staticmethod
    def get_templates_dir() -> Path:
        """Get the templates directory."""
        return EnvPaths.get_shared_state_dir() / "templates"

    @staticmethod
    def ensure_directories() -> None:
        """Ensure all required directories exist."""
        directories = [
            EnvPaths.get_root(),
            EnvPaths.get_skills_dir(),
            EnvPaths.get_shared_state_dir(),
            EnvPaths.get_backup_dir(),
            EnvPaths.get_log_dir(),
            EnvPaths.get_schema_dir(),
            EnvPaths.get_templates_dir(),
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def set_env_var(name: str, value: str) -> None:
        """
        Set an environment variable.

        Args:
            name: Environment variable name
            value: Value to set
        """
        os.environ[name] = value

    @staticmethod
    def get_env_var(name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get an environment variable.

        Args:
            name: Environment variable name
            default: Default value if not set

        Returns:
            Environment variable value or default
        """
        return os.environ.get(name, default)

    @staticmethod
    def print_env_vars() -> None:
        """Print all iFlow-related environment variables."""
        env_vars = [
            EnvPaths.ENV_IFLOW_ROOT,
            EnvPaths.ENV_SKILLS_DIR,
            EnvPaths.ENV_SHARED_STATE_DIR,
            EnvPaths.ENV_BACKUP_DIR,
            EnvPaths.ENV_LOG_DIR,
            EnvPaths.ENV_SCHEMA_DIR,
            EnvPaths.ENV_CONFIG_DIR,
        ]

        print("iFlow Environment Variables:")
        print("-" * 40)
        for var in env_vars:
            value = os.environ.get(var, "Not set")
            print(f"{var}: {value}")

    @staticmethod
    def validate_paths() -> bool:
        """
        Validate that all configured paths are accessible.

        Returns:
            True if all paths are valid, False otherwise
        """
        try:
            # Check if root exists
            root = EnvPaths.get_root()
            if not root.exists():
                _logger.warning(f"Root directory does not exist: {root}")

            # Check if skills dir exists
            skills_dir = EnvPaths.get_skills_dir()
            if not skills_dir.exists():
                _logger.warning(f"Skills directory does not exist: {skills_dir}")

            # Check if utils dir exists
            utils_dir = EnvPaths.get_utils_dir()
            if not utils_dir.exists():
                _logger.warning(f"Utils directory does not exist: {utils_dir}")
                return False

            return True

        except Exception as e:
            _logger.error(f"Error validating paths: {e}")
            return False


# Convenience functions for backward compatibility
def get_skills_dir() -> Path:
    """Get the skills directory (backward compatible)."""
    return EnvPaths.get_skills_dir()


def get_shared_state_dir() -> Path:
    """Get the shared state directory (backward compatible)."""
    return EnvPaths.get_shared_state_dir()


def get_backup_dir() -> Path:
    """Get the backup directory (backward compatible)."""
    return EnvPaths.get_backup_dir()


def get_log_dir() -> Path:
    """Get the log directory (backward compatible)."""
    return EnvPaths.get_log_dir()