"""Common Type Definitions for iFlow CLI Skills.

This module provides TypedDict definitions for common data structures
used throughout the iFlow CLI skills system to improve type safety.
"""

from enum import Enum
from typing import Any, TypedDict


class ScaleLevel(str, Enum):
    """Scale levels for project requirements."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class RequirementItem(TypedDict):
    """A single requirement item."""

    id: str
    description: str


class Requirements(TypedDict):
    """Requirements extracted from project specification."""

    functional: list[RequirementItem]
    non_functional: list[RequirementItem]
    constraints: list[str]
    scale: ScaleLevel


class ArchitectureComponent(TypedDict):
    """A single architecture component."""

    name: str
    type: str
    responsibilities: list[str]
    dependencies: list[str]


class ArchitectureDesign(TypedDict):
    """System architecture design."""

    pattern: str
    components: list[ArchitectureComponent]
    data_flow: list[str]
    technologies: list[str]


class ConfigValues(TypedDict):
    """Configuration values dictionary."""

    version: str
    auto_commit: bool
    # Additional config keys can be added as needed


class SkillConfig(TypedDict):
    """Skill configuration."""

    skill_name: str
    version: str
    config: ConfigValues


class PipelineStageStatus(str, Enum):
    """Pipeline stage status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStageResult(TypedDict):
    """Result of a pipeline stage execution."""

    stage_name: str
    status: PipelineStageStatus
    output: str | None
    error: str | None
    duration_seconds: float | None


class PipelineExecution(TypedDict):
    """Pipeline execution state."""

    pipeline_name: str
    status: str
    stages: list[PipelineStageResult]
    start_time: str
    end_time: str | None


class UserStory(TypedDict):
    """A user story."""

    id: str
    title: str
    description: str
    acceptance_criteria: list[str]
    priority: str
    story_points: int | None


class Feature(TypedDict):
    """A feature."""

    id: str
    name: str
    description: str
    user_stories: list[UserStory]
    priority: str


class GitCommitInfo(TypedDict):
    """Information about a git commit."""

    hash: str
    author: str
    date: str
    message: str
    files_changed: list[str]


class GitBranchInfo(TypedDict):
    """Information about a git branch."""

    name: str
    is_current: bool
    is_remote: bool
    commit_hash: str


class StateFileMetadata(TypedDict):
    """Metadata for a state file."""

    filename: str
    path: str
    last_modified: str
    size_bytes: int
    checksum: str | None


class ValidationResult(TypedDict):
    """Result of a validation operation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]


class SkillExecutionResult(TypedDict):
    """Result of a skill execution."""

    success: bool
    skill_name: str
    output: str | None
    error: str | None
    duration_seconds: float | None
    metadata: dict[str, Any]


class WorkflowState(TypedDict):
    """Workflow execution state."""

    workflow_name: str
    status: str
    current_step: str
    completed_steps: list[str]
    failed_steps: list[str]
    metadata: dict[str, Any]


class ReviewComment(TypedDict):
    """A review comment."""

    id: str
    author: str
    file_path: str
    line_number: int
    comment: str
    severity: str
    created_at: str


class ReviewResult(TypedDict):
    """Result of a code review."""

    review_id: str
    reviewer: str
    status: str
    comments: list[ReviewComment]
    overall_score: int | None
    approved: bool


class DependencyInfo(TypedDict):
    """Information about a dependency."""

    name: str
    version: str
    source: str
    is_required: bool
    security_issues: list[str]


class TestResult(TypedDict):
    """Result of a test execution."""

    test_name: str
    status: str
    duration_seconds: float
    error_message: str | None
    stack_trace: str | None


class TestSuiteResult(TypedDict):
    """Result of a test suite execution."""

    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration_seconds: float
    results: list[TestResult]


class SecurityFinding(TypedDict):
    """A security finding."""

    id: str
    severity: str
    title: str
    description: str
    file_path: str | None
    line_number: int | None
    recommendation: str


class SecurityScanResult(TypedDict):
    """Result of a security scan."""

    scan_type: str
    total_findings: int
    critical: int
    high: int
    medium: int
    low: int
    findings: list[SecurityFinding]


class DeploymentConfig(TypedDict):
    """Deployment configuration."""

    environment: str
    region: str
    service_name: str
    replicas: int
    resources: dict[str, str]
    environment_variables: dict[str, str]


class DeploymentStatus(TypedDict):
    """Status of a deployment."""

    deployment_id: str
    status: str
    environment: str
    started_at: str
    completed_at: str | None
    duration_seconds: float | None
    error_message: str | None


class DocumentationSection(TypedDict):
    """A documentation section."""

    title: str
    content: str
    subsections: list[DocumentationSection]


class DocumentationMetadata(TypedDict):
    """Metadata for documentation."""

    title: str
    version: str
    author: str
    created_at: str
    updated_at: str
    sections: list[DocumentationSection]


# Type aliases for common patterns
ConfigDict = dict[str, Any]
StateDict = dict[str, Any]
MetadataDict = dict[str, Any]
ErrorDict = dict[str, Any]
