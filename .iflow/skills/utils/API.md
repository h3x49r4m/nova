# iFlow Skills Utilities API Documentation

This document provides API documentation for all utility modules in the `.iflow/skills/utils/` directory.

## Table of Contents

- [Core Utilities](#core-utilities)
- [Error Handling](#error-handling)
- [Git Operations](#git-operations)
- [Validation](#validation)
- [State Management](#state-management)
- [Pipeline System](#pipeline-system)
- [Review System](#review-system)
- [Logging & Monitoring](#logging--monitoring)
- [Configuration](#configuration)
- [Caching](#caching)
- [Output & Formatting](#output--formatting)
- [Notifications](#notifications)

---

## Core Utilities

### `exceptions.py`

Custom exception hierarchy for iFlow operations.

```python
class IFlowError(Exception):
    """Base exception for all iFlow errors."""
    code: ErrorCode
    message: str

class ErrorCode(Enum):
    """Standard error codes."""
    SUCCESS = 0
    INVALID_INPUT = 1
    VALIDATION_FAILED = 2
    GIT_COMMAND_FAILED = 3
    FILE_NOT_FOUND = 4
    FILE_WRITE_ERROR = 5
    SECRET_DETECTED = 6
    TEST_FAILED = 7
    COVERAGE_BELOW_THRESHOLD = 8
    GIT_BRANCH_PROTECTED = 9
    UNKNOWN_ERROR = 99
```

**Usage:**
```python
from utils.exceptions import IFlowError, ErrorCode

raise IFlowError("Operation failed", ErrorCode.GIT_COMMAND_FAILED)
```

### `constants.py`

Centralized constants for iFlow operations.

```python
class Timeouts(Enum):
    """Timeout values for operations."""
    GIT_DEFAULT = 30
    TEST_DEFAULT = 60
    TEST_COVERAGE = 120
    PIPELINE_PHASE = 300

class CommitTypes(Enum):
    """Conventional commit types."""
    FEAT = "feat"
    FIX = "fix"
    DOCS = "docs"
    STYLE = "style"
    REFACTOR = "refactor"
    TEST = "test"
    CHORE = "chore"

class SecretPatterns(Enum):
    """Patterns for detecting secrets."""
    AWS_KEY = r"AKIA[0-9A-Z]{16}"
    API_KEY = r"api[_-]?key\s*=\s*['\"]?([a-zA-Z0-9_\-]+)"
    # ... more patterns
```

---

## Error Handling

### `error_message_formatter.py`

Formats error messages with context and suggestions.

```python
class ErrorMessageFormatter:
    def format_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        include_traceback: bool = False
    ) -> str:
        """Format error with context."""
```

### `error_recovery_strategies.py`

Provides recovery strategies for errors.

```python
class ErrorRecoveryManager:
    def get_recovery_strategy(
        self,
        error: Exception
    ) -> Optional[RecoveryStrategy]:
        """Get recovery strategy for error."""
    
    def apply_recovery(
        self,
        strategy: RecoveryStrategy,
        context: Dict[str, Any]
    ) -> bool:
        """Apply recovery strategy."""
```

### `error_translator.py`

Translates technical errors to user-friendly messages.

```python
class ErrorTranslator:
    def translate(
        self,
        error: Exception,
        audience: Audience
    ) -> str:
        """Translate error for audience."""
```

### `error_context_collector.py`

Collects debugging context for errors.

```python
class ErrorContextCollector:
    def collect_context(
        self,
        error: Exception
    ) -> ErrorContext:
        """Collect context for error."""
```

---

## Git Operations

### `git_command.py`

Provides standardized git command execution with safety checks.

```python
def run_git_command(
    command: List[str],
    cwd: Optional[Path] = None,
    timeout: int = 30,
    capture: bool = True,
    input_data: Optional[str] = None
) -> Tuple[int, str, str]:
    """Run git command with safety checks."""

def get_current_branch(cwd: Optional[Path] = None) -> str:
    """Get current git branch."""

def validate_branch_name(branch_name: str) -> Tuple[bool, Optional[str]]:
    """Validate git branch name."""

def validate_file_path(file_path: str) -> Tuple[bool, Optional[str]]:
    """Validate file path for git operations."""
```

### `file_lock.py`

Provides file locking for concurrent access prevention.

```python
class FileLock:
    def __init__(
        self,
        file_path: Path,
        timeout: int = 30,
        poll_interval: float = 0.1
    ):
        """Initialize file lock."""
    
    def acquire(self) -> bool:
        """Acquire lock."""
    
    def release(self) -> bool:
        """Release lock."""
    
    def __enter__(self) -> 'FileLock':
        """Context manager entry."""
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
```

---

## Validation

### `schema_validator.py`

Validates configuration files against schemas.

```python
class SchemaValidator:
    def validate(
        self,
        data: Dict[str, Any],
        schema_path: Path
    ) -> Tuple[bool, Optional[str]]:
        """Validate data against schema."""
```

### `json_schema_validator.py`

Provides JSON Schema validation.

```python
class JSONSchemaValidator:
    def validate(
        self,
        data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> ValidationResult:
        """Validate data against JSON schema."""
```

### `config_validator.py`

Validates configuration files.

```python
class ConfigValidator:
    def validate_config(
        self,
        config_path: Path,
        schema_path: Optional[Path] = None
    ) -> Tuple[bool, Optional[str]]:
        """Validate configuration file."""
```

### `field_validators.py`

Provides regex and pattern-based field validation.

```python
class FieldValidator:
    def validate_email(self, email: str) -> Tuple[bool, Optional[str]]:
        """Validate email address."""
    
    def validate_branch_name(self, branch_name: str) -> Tuple[bool, Optional[str]]:
        """Validate git branch name."""
    
    def validate_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Validate URL."""
```

### `document_validator.py`

Validates document content and completeness.

```python
class DocumentValidator:
    def validate_document(
        self,
        content: str,
        document_type: str
    ) -> DocumentValidationResult:
        """Validate document content."""
    
    def calculate_completeness(
        self,
        document: Dict[str, Any]
    ) -> float:
        """Calculate document completeness score."""
```

### `version_check.py`

Checks Python and Git version requirements.

```python
def check_python_version(min_version: str = "3.8") -> Tuple[bool, str]:
    """Check Python version."""

def check_git_version(min_version: str = "2.20") -> Tuple[bool, str]:
    """Check Git version."""

class VersionChecker:
    def check_all(self) -> Dict[str, Tuple[bool, str]]:
        """Check all version requirements."""
```

### `version_compatibility_validator.py`

Validates skill and pipeline compatibility.

```python
class VersionCompatibilityValidator:
    def check_skill_compatibility(
        self,
        skill_name: str,
        version: str
    ) -> CompatibilityResult:
        """Check skill version compatibility."""
    
    def check_pipeline_compatibility(
        self,
        pipeline_name: str,
        version: str
    ) -> CompatibilityResult:
        """Check pipeline version compatibility."""
```

---

## State Management

### `state_validator.py`

Validates state document consistency.

```python
class StateValidator:
    def validate_state(
        self,
        state_doc: Dict[str, Any]
    ) -> StateValidationResult:
        """Validate state document."""
    
    def validate_transitions(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Validate state transitions."""
```

### `state_conflict_resolver.py`

Resolves conflicts in shared state documents.

```python
class StateConflictResolver:
    def detect_conflicts(
        self,
        states: List[Dict[str, Any]]
    ) -> List[Conflict]:
        """Detect conflicts between states."""
    
    def resolve_conflict(
        self,
        conflict: Conflict,
        strategy: ConflictResolutionStrategy
    ) -> Dict[str, Any]:
        """Resolve state conflict."""
```

### `backup_manager.py`

Manages backups of critical state files.

```python
class BackupManager:
    def create_backup(
        self,
        file_path: Path,
        description: Optional[str] = None
    ) -> Backup:
        """Create backup of file."""
    
    def restore_backup(
        self,
        backup_id: str
    ) -> bool:
        """Restore from backup."""
    
    def list_backups(self, file_path: Optional[Path] = None) -> List[Backup]:
        """List available backups."""
```

### `audit_logger.py`

Provides audit logging for state changes.

```python
class AuditLogger:
    def log_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        actor: Optional[str] = None
    ):
        """Log audit event."""
    
    def get_history(
        self,
        limit: int = 100
    ) -> List[AuditEntry]:
        """Get audit history."""
```

### `checkpoint_manager.py`

Manages workflow checkpoints.

```python
class CheckpointManager:
    def create_checkpoint(
        self,
        workflow_id: str,
        state: Dict[str, Any],
        description: Optional[str] = None
    ) -> Checkpoint:
        """Create workflow checkpoint."""
    
    def restore_checkpoint(
        self,
        checkpoint_id: str
    ) -> Dict[str, Any]:
        """Restore workflow from checkpoint."""
```

---

## Pipeline System

### `pipeline_orchestrator.py`

Orchestrates pipeline execution across skills.

```python
class PipelineOrchestrator:
    def execute_pipeline(
        self,
        pipeline_config: PipelineConfig
    ) -> PipelineResult:
        """Execute pipeline."""
    
    def pause_pipeline(self, pipeline_id: str) -> bool:
        """Pause pipeline execution."""
    
    def resume_pipeline(self, pipeline_id: str) -> bool:
        """Resume pipeline execution."""
```

### `pipeline_state_manager.py`

Manages pipeline state persistence.

```python
class PipelineStateManager:
    def save_state(
        self,
        pipeline_id: str,
        state: PipelineState
    ):
        """Save pipeline state."""
    
    def load_state(
        self,
        pipeline_id: str
    ) -> Optional[PipelineState]:
        """Load pipeline state."""
```

### `skill_invoker.py`

Invokes skills with proper context and state management.

```python
class SkillInvoker:
    def invoke_skill(
        self,
        skill_name: str,
        context: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> SkillResult:
        """Invoke a skill."""
    
    def invoke_skill_sequence(
        self,
        skill_sequence: List[str],
        context: Dict[str, Any]
    ) -> List[SkillResult]:
        """Invoke skills in sequence."""
```

### `pipeline_git_flow_integration.py`

Integrates pipelines with git-flow workflow.

```python
class PipelineGitFlowIntegration:
    def integrate_pipeline(
        self,
        pipeline_config: PipelineConfig,
        git_flow: GitFlow
    ):
        """Integrate pipeline with git-flow."""
    
    def sync_state(
        self,
        pipeline_state: PipelineState,
        git_flow_state: Dict[str, Any]
    ):
        """Sync pipeline state with git-flow state."""
```

### `shared_state_coordinator.py`

Coordinates shared state between pipeline stages.

```python
class SharedStateCoordinator:
    def update_state(
        self,
        document_name: str,
        content: str,
        skill_name: str
    ):
        """Update shared state document."""
    
    def get_state(
        self,
        document_name: str
    ) -> Optional[str]:
        """Get shared state document."""
```

---

## Review System

### `review_engine.py`

Core review execution engine.

```python
class ReviewEngine:
    def execute_review(
        self,
        review_config: ReviewConfig
    ) -> ReviewResult:
        """Execute code review."""
    
    def execute_review_sequence(
        self,
        review_configs: List[ReviewConfig]
    ) -> List[ReviewResult]:
        """Execute multiple reviews."""
```

### `review_tool_integration.py`

Integrates external review tools.

```python
class ReviewToolIntegration:
    def run_sonarqube(self, project_path: Path) -> ReviewToolResult:
        """Run SonarQube analysis."""
    
    def run_snyk(self, project_path: Path) -> ReviewToolResult:
        """Run Snyk security scan."""
    
    def run_eslint(self, files: List[Path]) -> ReviewToolResult:
        """Run ESLint."""
```

### `review_rules.py`

Manages configurable review rules.

```python
class ReviewRulesManager:
    def register_rule(self, rule: ReviewRule):
        """Register review rule."""
    
    def evaluate_rules(
        self,
        context: Dict[str, Any]
    ) -> Tuple[List[Tuple[ReviewRule, bool, str]], bool]:
        """Evaluate all rules."""
```

### `review_aggregator.py`

Aggregates results from multiple review tools.

```python
class ReviewAggregator:
    def add_result(self, result: ReviewToolResult):
        """Add tool result."""
    
    def aggregate(self) -> AggregatedReviewResult:
        """Aggregate all results."""
    
    def export_report(self, output_file: Optional[Path] = None) -> str:
        """Export aggregated report."""
```

### `quality_gates.py`

Evaluates quality gates for workflows.

```python
class QualityGates:
    def evaluate(
        self,
        metrics: Dict[str, Any],
        gate_config: QualityGateConfig
    ) -> QualityGateResult:
        """Evaluate quality gates."""
    
    def check_blocking_gates(self, result: QualityGateResult) -> bool:
        """Check if any blocking gates failed."""
```

---

## Logging & Monitoring

### `structured_logger.py`

Structured logging with multiple formats.

```python
class StructuredLogger:
    def __init__(
        self,
        name: str,
        log_dir: Optional[Path] = None,
        log_format: LogFormat = LogFormat.JSON
    ):
        """Initialize structured logger."""
    
    def info(self, message: str, **kwargs):
        """Log info message."""
    
    def error(self, message: str, **kwargs):
        """Log error message."""
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
```

### `progress_indicator.py`

Visual progress tracking for long operations.

```python
class ProgressIndicator:
    def update(self, current: int, total: int):
        """Update progress."""
    
    def complete(self):
        """Mark as complete."""
```

### `deadlock_detector.py`

Detects deadlocks in git-flow dependencies.

```python
class DeadlockDetector:
    def detect_deadlocks(
        self,
        dependency_graph: Dict[str, List[str]]
    ) -> List[Deadlock]:
        """Detect circular dependencies."""
```

### `dependency_scanner.py`

Scans dependencies for security vulnerabilities.

```python
class DependencyScanner:
    def scan_python_dependencies(
        self,
        requirements_file: Optional[Path] = None
    ) -> Tuple[List[Vulnerability], Dict[str, Any]]:
        """Scan Python dependencies."""
```

---

## Configuration

### `default_config.py`

Centralized default configuration definitions.

```python
class DefaultConfig:
    @classmethod
    def get_git_flow_config(cls) -> Dict[str, Any]:
        """Get default git-flow configuration."""
    
    @classmethod
    def get_pipeline_config(cls) -> Dict[str, Any]:
        """Get default pipeline configuration."""
```

### `env_config_loader.py`

Loads configuration from environment variables.

```python
class EnvironmentConfigLoader:
    def load_config(
        self,
        prefix: str = "IFLOW_"
    ) -> Dict[str, Any]:
        """Load configuration from environment."""
    
    def get_variable(
        self,
        name: str,
        default: Optional[str] = None,
        var_type: ConfigVarType = ConfigVarType.STRING
    ) -> Any:
        """Get environment variable."""
```

### `profile_manager.py`

Manages environment profiles (dev/staging/prod).

```python
class ProfileManager:
    def load_profile(self, profile_name: str) -> Profile:
        """Load profile configuration."""
    
    def merge_configs(
        self,
        base_config: Dict[str, Any],
        profile_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge configurations."""
```

---

## Caching

### `cache_manager.py`

Provides caching for expensive operations.

```python
class CacheManager:
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """Set value in cache."""
    
    def cached(
        self,
        ttl: Optional[int] = None,
        key_prefix: str = ""
    ):
        """Decorator for caching function results."""
```

---

## Output & Formatting

### `output_templates.py`

Formats workflow results in multiple formats.

```python
class TemplateEngine:
    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """Render template with context."""
```

### `color_output.py`

Provides colored console output.

```python
class ColorConsole:
    def success(self, *args, **kwargs):
        """Print success message."""
    
    def error(self, *args, **kwargs):
        """Print error message."""
    
    def warning(self, *args, **kwargs):
        """Print warning message."""
```

### `handoff_protocol.py`

Manages formal handoffs between roles.

```python
class HandoffProtocol:
    def create_handoff(
        self,
        from_role: str,
        to_role: str,
        artifacts: List[str]
    ) -> Handoff:
        """Create handoff record."""
    
    def validate_handoff(
        self,
        handoff: Handoff
    ) -> Tuple[bool, Optional[str]]:
        """Validate handoff."""
```

---

## Notifications

### `notification_system.py`

Sends notifications for review results.

```python
class NotificationSystem:
    def send_notification(
        self,
        trigger: NotificationTrigger,
        title: str,
        message: str,
        severity: NotificationSeverity
    ) -> bool:
        """Send notification."""
    
    def add_channel(self, config: NotificationConfig):
        """Add notification channel."""
```

---

## Additional Utilities

### `tdd_enforcer.py`

Enforces Test-Driven Development practices.

```python
class TDDEnforcer:
    def validate_tdd_compliance(
        self,
        code_files: List[Path],
        test_files: List[Path]
    ) -> TDDResult:
        """Validate TDD compliance."""
```

### `prerequisite_checker.py`

Validates prerequisites before workflow execution.

```python
class PrerequisiteChecker:
    def check_prerequisites(
        self,
        prerequisites: List[Prerequisite]
    ) -> Tuple[bool, List[str]]:
        """Check all prerequisites."""
```

### `schema_version_manager.py`

Manages schema versions and migrations.

```python
class SchemaVersionManager:
    def migrate(
        self,
        data: Dict[str, Any],
        from_version: str,
        to_version: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Migrate data between versions."""
```

---

## Usage Examples

### Example 1: Using Git Commands

```python
from utils.git_command import run_git_command, get_current_branch
from utils.exceptions import IFlowError, ErrorCode

try:
    branch = get_current_branch()
    code, stdout, stderr = run_git_command(['status'])
    
    if code != 0:
        raise IFlowError(f"Git status failed: {stderr}", ErrorCode.GIT_COMMAND_FAILED)
        
except IFlowError as e:
    print(f"Error: {e.message}")
```

### Example 2: Using Cache

```python
from utils.cache_manager import CacheManager, CacheBackend

cache = CacheManager(
    backend=CacheBackend.MEMORY,
    max_size_mb=100,
    default_ttl=3600
)

@cache.cached(ttl=1800, key_prefix="api_")
def fetch_api_data(url: str):
    # Expensive operation
    return requests.get(url).json()

data = fetch_api_data("https://api.example.com/data")
```

### Example 3: Using Logger

```python
from utils.structured_logger import StructuredLogger, LogFormat

logger = StructuredLogger(
    name="my-app",
    log_dir=Path("./logs"),
    log_format=LogFormat.JSON
)

logger.info("Processing started", workflow_id="123", user="alice")
logger.error("Processing failed", error="timeout", retry_count=3)
```

### Example 4: Using Validation

```python
from utils.field_validators import FieldValidator
from utils.config_validator import ConfigValidator

validator = FieldValidator()

is_valid, error = validator.validate_email("user@example.com")
if not is_valid:
    print(f"Invalid email: {error}")

config_validator = ConfigValidator()
is_valid, error = config_validator.validate_config(Path("config.json"))
if not is_valid:
    print(f"Config error: {error}")
```

---

For more detailed information, see the source code in `.iflow/skills/utils/`.