"""Review Execution Engine - Executes automated code reviews.

This module provides a comprehensive engine for executing automated code reviews
using multiple review tools, with configurable rules, result aggregation, and
quality gate enforcement.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
import asyncio
import concurrent.futures

from .review_tool_integration import (
    ReviewToolIntegration,
    create_review_integration
)
from .quality_gates import (
    QualityGateEvaluator,
    QualityGateType,
    QualityGateStatus
)
from .exceptions import (
    IFlowError,
    ValidationError,
    ErrorCode,
    ErrorCategory
)
from .constants import Timeouts


class ReviewType(Enum):
    """Types of reviews."""
    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    LINTING = "linting"
    DEPENDENCY = "dependency"
    COMPREHENSIVE = "comprehensive"


class ReviewSeverity(Enum):
    """Severity levels for review findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ReviewStatus(Enum):
    """Status of a review execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReviewRule:
    """Represents a review rule."""
    
    def __init__(
        self,
        rule_id: str,
        name: str,
        description: str,
        severity: ReviewSeverity,
        tool: str,
        enabled: bool = True,
        condition: Optional[str] = None
    ):
        """
        Initialize a review rule.
        
        Args:
            rule_id: Unique identifier for the rule
            name: Human-readable name
            description: Description of what the rule checks
            severity: Severity level
            tool: Tool that applies this rule
            enabled: Whether the rule is enabled
            condition: Optional condition for when to apply the rule
        """
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.severity = severity
        self.tool = tool
        self.enabled = enabled
        self.condition = condition
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "tool": self.tool,
            "enabled": self.enabled,
            "condition": self.condition
        }


class ReviewFinding:
    """Represents a finding from a review."""
    
    def __init__(
        self,
        finding_id: str,
        rule_id: str,
        tool: str,
        severity: ReviewSeverity,
        message: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        column_number: Optional[int] = None,
        code_snippet: Optional[str] = None,
        fix_suggestion: Optional[str] = None,
        category: Optional[str] = None
    ):
        """
        Initialize a review finding.
        
        Args:
            finding_id: Unique identifier for the finding
            rule_id: ID of the rule that triggered this finding
            tool: Tool that generated this finding
            severity: Severity level
            message: Description of the finding
            file_path: Path to the file where the finding was detected
            line_number: Line number where the finding was detected
            column_number: Column number where the finding was detected
            code_snippet: Code snippet related to the finding
            fix_suggestion: Suggested fix for the finding
            category: Category of the finding
        """
        self.finding_id = finding_id
        self.rule_id = rule_id
        self.tool = tool
        self.severity = severity
        self.message = message
        self.file_path = file_path
        self.line_number = line_number
        self.column_number = column_number
        self.code_snippet = code_snippet
        self.fix_suggestion = fix_suggestion
        self.category = category
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "finding_id": self.finding_id,
            "rule_id": self.rule_id,
            "tool": self.tool,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "code_snippet": self.code_snippet,
            "fix_suggestion": self.fix_suggestion,
            "category": self.category,
            "timestamp": self.timestamp
        }


class ReviewResult:
    """Represents the result of a review."""
    
    def __init__(
        self,
        review_id: str,
        review_type: ReviewType,
        status: ReviewStatus = ReviewStatus.PENDING
    ):
        """
        Initialize a review result.
        
        Args:
            review_id: Unique identifier for the review
            review_type: Type of review performed
            status: Current status of the review
        """
        self.review_id = review_id
        self.review_type = review_type
        self.status = status
        self.findings: List[ReviewFinding] = []
        self.tool_results: Dict[str, Any] = {}
        self.metrics: Dict[str, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
            "total": 0
        }
        self.start_time: Optional[str] = None
        self.end_time: Optional[str] = None
        self.duration_seconds: Optional[float] = None
        self.quality_gate_status: Optional[QualityGateStatus] = None
        self.passed: bool = False
    
    def add_finding(self, finding: ReviewFinding):
        """Add a finding to the review result."""
        self.findings.append(finding)
        severity = finding.severity.value
        if severity in self.metrics:
            self.metrics[severity] += 1
        self.metrics["total"] += 1
    
    def mark_started(self):
        """Mark the review as started."""
        self.status = ReviewStatus.RUNNING
        self.start_time = datetime.now().isoformat()
    
    def mark_completed(self, passed: bool = False):
        """Mark the review as completed."""
        self.status = ReviewStatus.COMPLETED
        self.end_time = datetime.now().isoformat()
        if self.start_time:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            self.duration_seconds = (end - start).total_seconds()
        self.passed = passed
    
    def mark_failed(self, error_message: str):
        """Mark the review as failed."""
        self.status = ReviewStatus.FAILED
        self.end_time = datetime.now().isoformat()
        self.findings.append(ReviewFinding(
            finding_id=f"error_{self.review_id}",
            rule_id="execution_error",
            tool="review_engine",
            severity=ReviewSeverity.CRITICAL,
            message=f"Review execution failed: {error_message}"
        ))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert review result to dictionary."""
        return {
            "review_id": self.review_id,
            "review_type": self.review_type.value,
            "status": self.status.value,
            "findings": [f.to_dict() for f in self.findings],
            "tool_results": self.tool_results,
            "metrics": self.metrics,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "quality_gate_status": self.quality_gate_status.value if self.quality_gate_status else None,
            "passed": self.passed
        }


class ReviewEngine:
    """Engine for executing automated code reviews."""
    
    def __init__(
        self,
        review_tool_integration: Optional[ReviewToolIntegration] = None,
        rules_file: Optional[Path] = None
    ):
        """
        Initialize the review engine.
        
        Args:
            review_tool_integration: Review tool integration instance
            rules_file: Path to rules configuration file
        """
        self.review_tool_integration = review_tool_integration or create_review_integration()
        self.rules: Dict[str, ReviewRule] = {}
        self.quality_gate_evaluator = QualityGateEvaluator()
        self._load_rules(rules_file)
    
    def _load_rules(self, rules_file: Optional[Path]):
        """Load review rules from file."""
        if rules_file and rules_file.exists():
            try:
                with open(rules_file, 'r') as f:
                    data = json.load(f)
                
                for rule_data in data.get("rules", []):
                    rule = ReviewRule(
                        rule_id=rule_data["rule_id"],
                        name=rule_data["name"],
                        description=rule_data["description"],
                        severity=ReviewSeverity(rule_data["severity"]),
                        tool=rule_data["tool"],
                        enabled=rule_data.get("enabled", True),
                        condition=rule_data.get("condition")
                    )
                    self.rules[rule.rule_id] = rule
            except Exception as e:
                    self.logger.warning(f"Failed to load rule {rule_id}: {e}")
                    pass
        
        # Load default rules if no rules file or loading failed
        if not self.rules:
            self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default review rules."""
        default_rules = [
            ReviewRule(
                rule_id="security_high_severity",
                name="High Severity Security Issues",
                description="No high severity security vulnerabilities allowed",
                severity=ReviewSeverity.HIGH,
                tool="snyk"
            ),
            ReviewRule(
                rule_id="code_quality_gate",
                name="Code Quality Gate",
                description="Code quality score must be above threshold",
                severity=ReviewSeverity.MEDIUM,
                tool="sonarqube"
            ),
            ReviewRule(
                rule_id="lint_errors",
                name="Linting Errors",
                description="No linting errors allowed",
                severity=ReviewSeverity.HIGH,
                tool="eslint"
            ),
            ReviewRule(
                rule_id="pylint_convention",
                name="Python Code Conventions",
                description="Python code must follow PEP8 conventions",
                severity=ReviewSeverity.MEDIUM,
                tool="pylint"
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.rule_id] = rule
    
    def execute_review(
        self,
        project_path: Path,
        review_type: ReviewType = ReviewType.COMPREHENSIVE,
        review_id: Optional[str] = None,
        tools: Optional[List[str]] = None
    ) -> ReviewResult:
        """
        Execute a code review.
        
        Args:
            project_path: Path to the project to review
            review_type: Type of review to perform
            review_id: Optional custom review ID
            tools: Optional list of specific tools to use
            
        Returns:
            ReviewResult object with findings
        """
        if not review_id:
            review_id = f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        result = ReviewResult(
            review_id=review_id,
            review_type=review_type
        )
        
        try:
            result.mark_started()
            
            # Determine tools to use based on review type
            if tools:
                tools_to_run = tools
            else:
                tools_to_run = self._get_tools_for_review_type(review_type)
            
            # Run scans with review tool integration
            scan_results = self.review_tool_integration.run_all_scans(
                project_path=project_path,
                tool_names=tools_to_run
            )
            
            result.tool_results = scan_results
            
            # Parse findings from scan results
            self._parse_findings(scan_results, result)
            
            # Evaluate quality gates
            result.quality_gate_status = self._evaluate_quality_gates(result)
            
            # Determine if review passed
            result.passed = result.quality_gate_status == QualityGateStatus.PASSED
            
            result.mark_completed(passed=result.passed)
            
        except Exception as e:
            result.mark_failed(str(e))
        
        return result
    
    def _get_tools_for_review_type(self, review_type: ReviewType) -> List[str]:
        """Get tools to use for a given review type."""
        tool_mapping = {
            ReviewType.CODE_QUALITY: ["sonarqube", "eslint", "pylint"],
            ReviewType.SECURITY: ["snyk"],
            ReviewType.LINTING: ["eslint", "pylint"],
            ReviewType.DEPENDENCY: ["snyk"],
            ReviewType.COMPREHENSIVE: ["sonarqube", "snyk", "eslint", "pylint"]
        }
        return tool_mapping.get(review_type, [])
    
    def _parse_findings(self, scan_results: Dict[str, Any], result: ReviewResult):
        """Parse findings from scan results."""
        for tool_name, tool_result in scan_results.get("results", {}).items():
            if not tool_result.get("success", False):
                continue
            
            findings_count = 0
            
            # Parse vulnerabilities from Snyk
            if tool_name == "snyk" and "vulnerabilities" in tool_result:
                for vuln in tool_result["vulnerabilities"]:
                    finding = ReviewFinding(
                        finding_id=f"snyk_{findings_count}_{result.review_id}",
                        rule_id="security_vulnerability",
                        tool=tool_name,
                        severity=self._map_snyk_severity(vuln.get("severity", "")),
                        message=vuln.get("title", ""),
                        category="security"
                    )
                    result.add_finding(finding)
                    findings_count += 1
            
            # Parse issues from ESLint
            elif tool_name == "eslint" and "issues" in tool_result:
                for issue in tool_result["issues"]:
                    finding = ReviewFinding(
                        finding_id=f"eslint_{findings_count}_{result.review_id}",
                        rule_id=issue.get("ruleId", "eslint_error"),
                        tool=tool_name,
                        severity=self._map_eslint_severity(issue.get("severity", 0)),
                        message=issue.get("message", ""),
                        file_path=issue.get("filePath"),
                        line_number=issue.get("line"),
                        column_number=issue.get("column"),
                        category="code_quality"
                    )
                    result.add_finding(finding)
                    findings_count += 1
            
            # Parse issues from Pylint
            elif tool_name == "pylint" and "issues" in tool_result:
                for issue in tool_result["issues"]:
                    finding = ReviewFinding(
                        finding_id=f"pylint_{findings_count}_{result.review_id}",
                        rule_id=issue.get("message-id", "pylint_issue"),
                        tool=tool_name,
                        severity=self._map_pylint_severity(issue.get("type", "")),
                        message=issue.get("message", ""),
                        file_path=issue.get("path"),
                        line_number=issue.get("line"),
                        column_number=issue.get("column"),
                        category="code_quality"
                    )
                    result.add_finding(finding)
                    findings_count += 1
    
    def _map_snyk_severity(self, snyk_severity: str) -> ReviewSeverity:
        """Map Snyk severity to ReviewSeverity."""
        severity_map = {
            "critical": ReviewSeverity.CRITICAL,
            "high": ReviewSeverity.HIGH,
            "medium": ReviewSeverity.MEDIUM,
            "low": ReviewSeverity.LOW
        }
        return severity_map.get(snyk_severity.lower(), ReviewSeverity.MEDIUM)
    
    def _map_eslint_severity(self, eslint_severity: int) -> ReviewSeverity:
        """Map ESLint severity to ReviewSeverity."""
        if eslint_severity == 2:
            return ReviewSeverity.HIGH
        elif eslint_severity == 1:
            return ReviewSeverity.MEDIUM
        return ReviewSeverity.LOW
    
    def _map_pylint_severity(self, pylint_type: str) -> ReviewSeverity:
        """Map Pylint type to ReviewSeverity."""
        type_map = {
            "fatal": ReviewSeverity.CRITICAL,
            "error": ReviewSeverity.HIGH,
            "warning": ReviewSeverity.MEDIUM,
            "convention": ReviewSeverity.LOW,
            "refactor": ReviewSeverity.LOW,
            "info": ReviewSeverity.INFO
        }
        return type_map.get(pylint_type.lower(), ReviewSeverity.LOW)
    
    def _evaluate_quality_gates(self, result: ReviewResult) -> QualityGateStatus:
        """Evaluate quality gates for the review result."""
        # Build metrics for quality gate evaluation
        metrics = {
            "bug_severity": {
                "critical": result.metrics["critical"],
                "high": result.metrics["high"],
                "medium": result.metrics["medium"]
            },
            "security_scan": {
                "high": result.metrics["high"]
            },
            "test_coverage": 80.0,  # Default placeholder
            "lint_errors": result.metrics["critical"] + result.metrics["high"]
        }
        
        # Evaluate all quality gates
        status = self.quality_gate_evaluator.evaluate_all(metrics)
        
        return status
    
    def add_rule(self, rule: ReviewRule):
        """Add a review rule."""
        self.rules[rule.rule_id] = rule
    
    def remove_rule(self, rule_id: str):
        """Remove a review rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all review rules."""
        return [rule.to_dict() for rule in self.rules.values()]
    
    def save_review_result(self, result: ReviewResult, output_file: Path):
        """
        Save review result to file.
        
        Args:
            result: ReviewResult to save
            output_file: Path to output file
        """
        try:
            with open(output_file, 'w') as f:
                json.dump(result.to_dict(), f, indent=2)
        except Exception as e:
            raise IFlowError(
                f"Failed to save review result: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def generate_report(self, result: ReviewResult) -> str:
        """
        Generate a human-readable report for a review result.
        
        Args:
            result: ReviewResult to generate report for
            
        Returns:
            Formatted report string
        """
        lines = [
            f"Code Review Report",
            f"=" * 50,
            f"Review ID: {result.review_id}",
            f"Type: {result.review_type.value}",
            f"Status: {result.status.value}",
            f"Passed: {'YES' if result.passed else 'NO'}",
            f"",
            f"Duration: {result.duration_seconds:.2f}s" if result.duration_seconds else "Duration: N/A",
            f"",
            f"Findings Summary",
            f"-" * 50
        ]
        
        for severity, count in result.metrics.items():
            if severity != "total":
                lines.append(f"  {severity.capitalize()}: {count}")
        
        lines.append(f"  Total: {result.metrics['total']}")
        lines.append("")
        
        if result.findings:
            lines.append("Detailed Findings")
            lines.append("-" * 50)
            
            for finding in result.findings:
                lines.append(f"\n[{finding.severity.value.upper()}] {finding.message}")
                if finding.file_path:
                    location = finding.file_path
                    if finding.line_number:
                        location += f":{finding.line_number}"
                    lines.append(f"  Location: {location}")
                if finding.tool:
                    lines.append(f"  Tool: {finding.tool}")
                if finding.fix_suggestion:
                    lines.append(f"  Suggestion: {finding.fix_suggestion}")
        else:
            lines.append("No findings detected.")
        
        return "\n".join(lines)


def create_review_engine(
    config: Optional[Dict[str, Any]] = None,
    rules_file: Optional[Path] = None
) -> ReviewEngine:
    """Create a review engine instance."""
    integration = create_review_integration(config) if config else None
    return ReviewEngine(
        review_tool_integration=integration,
        rules_file=rules_file
    )