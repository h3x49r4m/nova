#!/usr/bin/env python3
"""
Base Classes for Skills and Pipelines
Provides abstract base classes for consistent skill and pipeline implementations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class SkillStatus(Enum):
    """Skill execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStatus(Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class SkillResult:
    """Result of a skill execution."""

    def __init__(
        self,
        success: bool,
        output: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.output = output
        self.error = error
        self.metadata = metadata or {}
        self.execution_time_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
            "execution_time_ms": self.execution_time_ms
        }


class BaseSkill(ABC):
    """
    Abstract base class for all skills.

    All skill implementations should inherit from this class to ensure
    consistent interface and behavior across the iFlow CLI skills system.
    """

    def __init__(self, skill_name: str, config_path: Optional[Path] = None):
        """
        Initialize the skill.

        Args:
            skill_name: Name of the skill
            config_path: Optional path to skill configuration file
        """
        self.skill_name = skill_name
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.status = SkillStatus.PENDING

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the skill name.

        Returns:
            Skill name
        """
        pass

    @abstractmethod
    def get_version(self) -> str:
        """
        Get the skill version.

        Returns:
            Version string (e.g., "1.0.0")
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        Get the skill description.

        Returns:
            Description of what the skill does
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """
        Get the list of capabilities this skill provides.

        Returns:
            List of capability names
        """
        pass

    def load_config(self) -> None:
        """Load skill configuration from config_path."""
        if self.config_path and self.config_path.exists():
            import json
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    @abstractmethod
    def validate_prerequisites(self, project_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate that all prerequisites are met for skill execution.

        Args:
            project_path: Path to the project directory

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    def execute(
        self,
        project_path: Path,
        **kwargs
    ) -> SkillResult:
        """
        Execute the skill.

        Args:
            project_path: Path to the project directory
            **kwargs: Additional skill-specific parameters

        Returns:
            SkillResult containing execution outcome
        """
        pass

    def can_execute(self, project_path: Path) -> bool:
        """
        Check if the skill can be executed on the given project.

        Args:
            project_path: Path to the project directory

        Returns:
            True if skill can execute, False otherwise
        """
        is_valid, _ = self.validate_prerequisites(project_path)
        return is_valid

    def get_status(self) -> SkillStatus:
        """
        Get the current status of the skill.

        Returns:
            Current skill status
        """
        return self.status

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.get_name()}', version='{self.get_version()}')"


class BasePipeline(ABC):
    """
    Abstract base class for all pipelines.

    All pipeline implementations should inherit from this class to ensure
    consistent interface and behavior across the iFlow CLI pipeline system.
    """

    def __init__(self, pipeline_name: str, config_path: Optional[Path] = None):
        """
        Initialize the pipeline.

        Args:
            pipeline_name: Name of the pipeline
            config_path: Optional path to pipeline configuration file
        """
        self.pipeline_name = pipeline_name
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.status = PipelineStatus.PENDING
        self.stages: List['PipelineStage'] = []

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the pipeline name.

        Returns:
            Pipeline name
        """
        pass

    @abstractmethod
    def get_version(self) -> str:
        """
        Get the pipeline version.

        Returns:
            Version string (e.g., "1.0.0")
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        Get the pipeline description.

        Returns:
            Description of what the pipeline does
        """
        pass

    @abstractmethod
    def get_stages(self) -> List['PipelineStage']:
        """
        Get the stages in this pipeline.

        Returns:
            List of pipeline stages
        """
        pass

    @abstractmethod
    def get_required_skills(self) -> List[str]:
        """
        Get the list of skills required by this pipeline.

        Returns:
            List of skill names
        """
        pass

    def load_config(self) -> None:
        """Load pipeline configuration from config_path."""
        if self.config_path and self.config_path.exists():
            import json
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    @abstractmethod
    def validate_prerequisites(self, project_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate that all prerequisites are met for pipeline execution.

        Args:
            project_path: Path to the project directory

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    def execute(
        self,
        project_path: Path,
        **kwargs
    ) -> SkillResult:
        """
        Execute the pipeline.

        Args:
            project_path: Path to the project directory
            **kwargs: Additional pipeline-specific parameters

        Returns:
            SkillResult containing execution outcome
        """
        pass

    def can_execute(self, project_path: Path) -> bool:
        """
        Check if the pipeline can be executed on the given project.

        Args:
            project_path: Path to the project directory

        Returns:
            True if pipeline can execute, False otherwise
        """
        is_valid, _ = self.validate_prerequisites(project_path)
        return is_valid

    def get_status(self) -> PipelineStatus:
        """
        Get the current status of the pipeline.

        Returns:
            Current pipeline status
        """
        return self.status

    def get_progress(self) -> float:
        """
        Get the pipeline execution progress as a percentage.

        Returns:
            Progress percentage (0-100)
        """
        if not self.stages:
            return 0.0

        completed = sum(1 for stage in self.stages if stage.status == SkillStatus.COMPLETED)
        return (completed / len(self.stages)) * 100

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.get_name()}', version='{self.get_version()}')"


class PipelineStage:
    """
    Represents a single stage in a pipeline.

    A stage contains one or more skills that should be executed together.
    """

    def __init__(
        self,
        name: str,
        skills: List[BaseSkill],
        dependencies: Optional[List[str]] = None,
        optional: bool = False
    ):
        """
        Initialize a pipeline stage.

        Args:
            name: Name of the stage
            skills: List of skills to execute in this stage
            dependencies: List of stage names this stage depends on
            optional: Whether this stage is optional (can be skipped on failure)
        """
        self.name = name
        self.skills = skills
        self.dependencies = dependencies or []
        self.optional = optional
        self.status = SkillStatus.PENDING
        self.result: Optional[SkillResult] = None

    def can_execute(self, completed_stages: List[str]) -> bool:
        """
        Check if this stage can be executed based on dependencies.

        Args:
            completed_stages: List of completed stage names

        Returns:
            True if all dependencies are met, False otherwise
        """
        return all(dep in completed_stages for dep in self.dependencies)

    def execute(self, project_path: Path, **kwargs) -> SkillResult:
        """
        Execute all skills in this stage.

        Args:
            project_path: Path to the project directory
            **kwargs: Additional parameters

        Returns:
            SkillResult containing combined outcome
        """
        self.status = SkillStatus.RUNNING
        results = []

        for skill in self.skills:
            result = skill.execute(project_path, **kwargs)
            results.append(result)

            if not result.success and not self.optional:
                self.status = SkillStatus.FAILED
                self.result = SkillResult(
                    success=False,
                    error=f"Stage failed: {result.error}"
                )
                return self.result

        self.status = SkillStatus.COMPLETED
        self.result = SkillResult(
            success=True,
            output=f"Stage completed with {len(results)} skills"
        )
        return self.result

    def __repr__(self) -> str:
        return f"PipelineStage(name='{self.name}', skills={len(self.skills)})"