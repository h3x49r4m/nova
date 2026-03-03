#!/usr/bin/env python3
"""
Centralized Constants
Defines all magic numbers, timeouts, and configuration constants used across the skills system.
"""

from enum import Enum
from typing import Tuple


class Timeouts(Enum):
    """Timeout values for various operations."""
    GIT_DEFAULT = 120
    GIT_PULL = 180
    GIT_PUSH = 300
    GIT_CLONE = 600
    TEST_DEFAULT = 300
    FILE_LOCK_DEFAULT = 10
    STATE_LOAD = 30
    STATE_SAVE = 30
    VALIDATION = 60
    SCAN_TIMEOUT = 600
    LINT_TIMEOUT = 300


class RetryPolicy(Enum):
    """Retry policy configuration."""
    MAX_ATTEMPTS = 3
    INITIAL_DELAY = 1  # seconds
    MAX_DELAY = 30  # seconds
    BACKOFF_FACTOR = 2


class GitBranches(Enum):
    """Standard protected branch names."""
    MAIN = "main"
    MASTER = "master"
    DEVELOP = "develop"
    PRODUCTION = "production"


class SemVer(Enum):
    """Semantic versioning constants."""
    MAJOR = 0
    MINOR = 1
    PATCH = 2


class CoverageThresholds(Enum):
    """Default coverage thresholds (as percentages)."""
    LINES = 80
    BRANCHES = 70
    FUNCTIONS = 80
    STATEMENTS = 80


class FileSizeLimits(Enum):
    """File size limits in bytes."""
    MAX_DIFF_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_FILE_READ = 100 * 1024 * 1024  # 100MB
    MAX_LOG_SIZE = 50 * 1024 * 1024  # 50MB


class BufferSizes(Enum):
    """Buffer and chunk sizes for I/O operations."""
    DEFAULT_BUFFER_SIZE = 8192  # 8KB
    FILE_READ_CHUNK_SIZE = 4096  # 4KB
    HASH_CHUNK_SIZE = 4096  # 4KB
    MAX_CACHE_KEY_SIZE = 200  # characters


class Percentages(Enum):
    """Percentage thresholds and calculations."""
    MIN_PERCENT = 0
    MAX_PERCENT = 100
    DEFAULT_PROGRESS_TOTAL = 100


class MemoryLimits(Enum):
    """Memory-related limits."""
    MIN_DISK_SPACE_MB = 100  # Minimum disk space in MB
    MAX_STRING_LENGTH = 500  # Maximum string length for error contexts
    MAX_PROMPT_PREVIEW = 100  # Characters to show in prompt preview
    MAX_HISTORY_ENTRIES = 100  # Maximum history entries to keep


class BackupPolicy(Enum):
    """Backup policy configuration."""
    MAX_BACKUPS = 10
    RETENTION_DAYS = 30


class CachePolicy(Enum):
    """Cache policy configuration."""
    DEFAULT_TTL = 3600  # 1 hour in seconds
    MAX_SIZE = 1000  # max number of items


class ValidationPatterns(Enum):
    """Patterns for validation."""
    BRANCH_MAX_LENGTH = 255
    COMMIT_MAX_LENGTH = 72
    FILE_MAX_LENGTH = 4096
    TAG_MAX_LENGTH = 128


class SystemRequirements(Enum):
    """Minimum system requirements."""
    PYTHON_MIN_VERSION = (3, 14)  # Python 3.14+
    GIT_MIN_VERSION = (2, 30, 0)  # Git 2.30+


class BackupConstants(Enum):
    """Backup system constants."""
    MAX_BACKUPS_PER_FILE = 10
    BACKUP_RETENTION_DAYS = 30
    MAX_BACKUP_SIZE_MB = 100
    COMPRESSION_THRESHOLD_MB = 10


class AuditConstants(Enum):
    """Audit logging constants."""
    MAX_INDEX_EVENTS = 1000
    LOG_RETENTION_DAYS = 90
    LOG_MAX_SIZE_MB = 50
    LOG_ROTATION_SIZE_LINES = 10000


class LoggingConstants(Enum):
    """Logging configuration constants."""
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_LOG_FORMAT = "json"
    MAX_LOG_FILE_SIZE_MB = 10
    LOG_BACKUP_COUNT = 5
    LOG_DIR = ".iflow/logs"


class PhaseTimeouts(Enum):
    DEFAULT_PHASE_TIMEOUT = 604800  # 7 days in seconds
    MIN_PHASE_TIMEOUT = 86400  # 1 day
    MAX_PHASE_TIMEOUT = 2592000  # 30 days
    TIMEOUT_WARNING_THRESHOLD = 0.8  # 80% of timeout


class WorkflowConstants(Enum):
    """Workflow-related constants."""
    MAX_PHASES = 20
    MAX_DEPENDENCIES = 10
    MAX_SKILLS = 20


class SecretPatterns(Enum):
    """Patterns for detecting secrets in code."""
    API_KEY = r"api[_-]?key\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{20,}"
    SECRET = r"secret\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{20,}"
    TOKEN = r"token\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{20,}"
    ACCESS_TOKEN = r"access[_-]?token\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{20,}"
    PASSWORD = r"password\s*[=:]\s*['\"]?[^\s'\"]{8,}"
    PASSWD = r"passwd\s*[=:]\s*['\"]?[^\s'\"]{8,}"
    PRIVATE_KEY = r"private[_-]?key\s*[=:]\s*['\"]?-----BEGIN"
    BEGIN_PRIVATE_KEY = r"-----BEGIN [A-Z ]+PRIVATE KEY-----"
    JWT_TOKEN = r"(ey[A-Za-z0-9_-]{10,}\.ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})"
    AWS_ACCESS_KEY = r"aws[_-]?access[_-]?key[_-]?id\s*[=:]\s*['\"]?[A-Z0-9]{20}"
    AWS_SECRET_KEY = r"aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9+/]{40}"
    BEARER_TOKEN = r"bearer\s+[A-Za-z0-9\-._~+/]+=*"
    BASIC_AUTH = r"basic\s+[A-Za-z0-9+/=]+"
    OAUTH_TOKEN = r"oauth[_-]?token\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{20,}"
    REFRESH_TOKEN = r"refresh[_-]?token\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{20,}"
    SESSION_KEY = r"session[_-]?key\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{20,}"
    AUTHORIZATION_HEADER = r"authorization\s*:\s*['\"]?(bearer|basic)\s+[^\s'\"]+"
    DATABASE_URL = r"database[_-]?url\s*[=:]\s*['\"]?[^\s'\"]+://[^\s'\"]+:[^\s'\"]+"
    DB_PASSWORD = r"(db[_-]?(password|pass)|password[_-]?db)\s*[=:]\s*['\"]?[^\s'\"]{8,}"
    GITHUB_TOKEN = r"github[_-]?token\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{36,}"
    GITLAB_TOKEN = r"gitlab[_-]?token\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{20,}"
    SLACK_TOKEN = r"slack[_-]?token\s*[=:]\s*['\"]?xox[baprs]-[a-zA-Z0-9-]+"
    STRIPE_KEY = r"stripe[_-]?(api[_-]?key|secret[_-]?key)\s*[=:]\s*['\"]?sk_(test|live)_[a-zA-Z0-9]+"
    FIREBASE_KEY = r"firebase[_-]?(api[_-]?key|private[_-]?key)\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{20,}"
    HEROKU_API_KEY = r"heroku[_-]?api[_-]?key\s*[=:]\s*['\"]?[a-f0-9]{32}"
    HEROKU_AUTH_TOKEN = r"heroku[_-]?auth[_-]?token\s*[=:]\s*['\"]?[a-f0-9]{64}"
    TWITTER_API_KEY = r"twitter[_-]?api[_-]?key\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{25,}"
    TWITTER_SECRET = r"twitter[_-]?api[_-]?secret\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{50,}"
    GOOGLE_API_KEY = r"google[_-]?api[_-]?key\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{39}"
    GOOGLE_CLIENT_SECRET = r"google[_-]?client[_-]?secret\s*[=:]\s*['\"]?[a-zA-Z0-9_-]{24}"
    AZURE_STORAGE_KEY = r"azure[_-]?storage[_-]?(account[_-]?key|connection[_-]?string)\s*[=:]\s*['\"]?[a-zA-Z0-9/+]{88,}"
    SSH_PRIVATE_KEY = r"ssh[-_]?(rsa|ecdsa|ed25519)[_-]?(private[_-]?key|key)\s*[=:]\s*['\"]?-----BEGIN"
    ENCRYPTED_VALUE = r"encrypted\s*[=:]\s*['\"]?[a-zA-Z0-9+/]{100,}"


class CommitTypes(Enum):
    """Conventional commit types."""
    FEAT = "feat"
    FIX = "fix"
    REFACTOR = "refactor"
    TEST = "test"
    DOCS = "docs"
    CHORE = "chore"
    PERF = "perf"
    STYLE = "style"
    BUILD = "build"
    CI = "ci"


class PhaseStatus(Enum):
    """Phase status values."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    BLOCKED = "blocked"


class BranchStatus(Enum):
    """Branch status values."""
    PENDING = "pending"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    MERGED = "merged"
    UNAPPROVED = "unapproved"
    REVERTED = "reverted"
    NEEDS_CHANGES = "needs_changes"
    REJECTED = "rejected"


class WorkflowStatus(Enum):
    """Workflow status values."""
    INITIALIZED = "initialized"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    PAUSED = "paused"
    BLOCKED = "blocked"


class Environment(Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# Default configuration values
DEFAULT_PROTECTED_BRANCHES = [
    GitBranches.MAIN.value,
    GitBranches.MASTER.value,
    GitBranches.PRODUCTION.value
]

DEFAULT_COMMIT_TYPES = {ct.value: ct.value.title() for ct in CommitTypes}

DEFAULT_COVERAGE_THRESHOLDS = {
    "lines": CoverageThresholds.LINES.value,
    "branches": CoverageThresholds.BRANCHES.value,
    "functions": CoverageThresholds.FUNCTIONS.value,
    "statements": CoverageThresholds.STATEMENTS.value
}

# Version compatibility
MIN_PYTHON_VERSION = (3, 14)
MIN_GIT_VERSION = (2, 30, 0)

# Path constants
SKILLS_DIR = ".iflow/skills"
SHARED_STATE_DIR = ".iflow/skills/.shared-state"
BACKUP_DIR = ".iflow/skills/backups"
LOG_DIR = ".iflow/logs"

# File extensions
PYTHON_EXT = ".py"
JSON_EXT = ".json"
MD_EXT = ".md"

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


def get_timeout(operation: Timeouts) -> int:
    """
    Get timeout value for an operation.

    Args:
        operation: Timeouts enum value

    Returns:
        Timeout in seconds
    """
    return operation.value


def get_coverage_threshold(coverage_type: str = "lines") -> int:
    """
    Get coverage threshold for a type.

    Args:
        coverage_type: Type of coverage (lines, branches, functions, statements)

    Returns:
        Threshold percentage
    """
    return DEFAULT_COVERAGE_THRESHOLDS.get(coverage_type, CoverageThresholds.LINES.value)


def is_protected_branch(branch_name: str) -> bool:
    """
    Check if a branch is protected.

    Args:
        branch_name: Name of the branch to check

    Returns:
        True if branch is protected
    """
    return branch_name in DEFAULT_PROTECTED_BRANCHES


def get_secret_patterns() -> Tuple[str, ...]:
    """
    Get all secret detection patterns.

    Returns:
        Tuple of regex patterns
    """
    return tuple(pattern.value for pattern in SecretPatterns)


class ReviewToolConstants(Enum):
    """Review tool configuration constants."""
    SCAN_TIMEOUT = 300  # 5 minutes
    MAX_FINDINGS = 1000
    CRITICAL_SEVERITY = "critical"
    HIGH_SEVERITY = "high"
    MEDIUM_SEVERITY = "medium"
    LOW_SEVERITY = "low"


class LoggingConstants(Enum):
    """Logging configuration constants."""
    LOG_MAX_SIZE_MB = 50
    LOG_ROTATION_SIZE_LINES = 10000
    LOG_RETENTION_DAYS = 90
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_LOG_FORMAT = "json"
    MAX_BACKUP_COUNT = 5