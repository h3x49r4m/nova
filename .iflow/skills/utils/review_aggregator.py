"""Review Result Aggregator - Aggregates results from multiple review tools.

This module provides functionality for aggregating and normalizing results
from multiple code review tools into a unified format.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import IFlowError, ErrorCode
from .review_rules import RuleSeverity


class FindingSeverity(Enum):
    """Severity levels for findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(Enum):
    """Categories of findings."""
    SECURITY = "security"
    CODE_QUALITY = "code_quality"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"
    NAMING = "naming"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ReviewFinding:
    """Represents a code review finding."""
    tool: str
    tool_version: str = ""
    severity: FindingSeverity = FindingSeverity.INFO
    category: FindingCategory = FindingCategory.INFO
    title: str = ""
    description: str = ""
    file_path: str = ""
    line_number: int = 0
    column_number: int = 0
    code_snippet: str = ""
    rule_id: str = ""
    url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "tool": self.tool,
            "tool_version": self.tool_version,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "code_snippet": self.code_snippet,
            "rule_id": self.rule_id,
            "url": self.url,
            "metadata": self.metadata,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReviewFinding':
        """Create from dictionary."""
        return cls(
            tool=data.get("tool", ""),
            tool_version=data.get("tool_version", ""),
            severity=FindingSeverity(data.get("severity", "info")),
            category=FindingCategory(data.get("category", "info")),
            title=data.get("title", ""),
            description=data.get("description", ""),
            file_path=data.get("file_path", ""),
            line_number=data.get("line_number", 0),
            column_number=data.get("column_number", 0),
            code_snippet=data.get("code_snippet", ""),
            rule_id=data.get("rule_id", ""),
            url=data.get("url", ""),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now().isoformat())
        )


@dataclass
class ReviewToolResult:
    """Represents results from a single review tool."""
    tool_name: str
    tool_version: str = ""
    success: bool = False
    error_message: str = ""
    execution_time_seconds: float = 0.0
    findings: List[ReviewFinding] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "tool_name": self.tool_name,
            "tool_version": self.tool_version,
            "success": self.success,
            "error_message": self.error_message,
            "execution_time_seconds": self.execution_time_seconds,
            "findings": [f.to_dict() for f in self.findings],
            "metrics": self.metrics,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReviewToolResult':
        """Create from dictionary."""
        return cls(
            tool_name=data["tool_name"],
            tool_version=data.get("tool_version", ""),
            success=data["success"],
            error_message=data.get("error_message", ""),
            execution_time_seconds=data.get("execution_time_seconds", 0.0),
            findings=[ReviewFinding.from_dict(f) for f in data.get("findings", [])],
            metrics=data.get("metrics", {}),
            created_at=data.get("created_at", datetime.now().isoformat())
        )


@dataclass
class AggregatedReviewResult:
    """Represents aggregated results from multiple tools."""
    scan_time: str
    tools_scanned: List[str] = field(default_factory=list)
    tools_failed: List[str] = field(default_factory=list)
    total_findings: int = 0
    findings_by_severity: Dict[str, int] = field(default_factory=dict)
    findings_by_category: Dict[str, int] = field(default_factory=dict)
    findings_by_tool: Dict[str, int] = field(default_factory=dict)
    findings: List[ReviewFinding] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregated result to dictionary."""
        return {
            "scan_time": self.scan_time,
            "tools_scanned": self.tools_scanned,
            "tools_failed": self.tools_failed,
            "total_findings": self.total_findings,
            "findings_by_severity": self.findings_by_severity,
            "findings_by_category": self.findings_by_category,
            "findings_by_tool": self.findings_by_tool,
            "findings": [f.to_dict() for f in self.findings],
            "metrics": self.metrics,
            "created_at": self.created_at
        }


class ReviewAggregator:
    """Aggregates review results from multiple tools."""
    
    def __init__(self):
        """Initialize the review aggregator."""
        self.tool_results: List[ReviewToolResult] = []
        self.severity_mapping = {
            "critical": FindingSeverity.CRITICAL,
            "high": FindingSeverity.HIGH,
            "medium": FindingSeverity.MEDIUM,
            "low": FindingSeverity.LOW,
            "info": FindingSeverity.INFO,
            "error": FindingSeverity.HIGH,
            "warning": FindingSeverity.MEDIUM
        }
        self.category_mapping = {
            "security": FindingCategory.SECURITY,
            "code_quality": FindingCategory.CODE_QUALITY,
            "performance": FindingCategory.PERFORMANCE,
            "maintainability": FindingCategory.MAINTAINABILITY,
            "style": FindingCategory.STYLE,
            "documentation": FindingCategory.DOCUMENTATION,
            "testing": FindingCategory.TESTING,
            "complexity": FindingCategory.COMPLEXITY,
            "duplication": FindingCategory.DUPLICATION,
            "naming": FindingCategory.NAMING,
            "error": FindingCategory.ERROR,
            "warning": FindingCategory.WARNING
        }
    
    def add_result(self, result: ReviewToolResult):
        """
        Add a tool result.
        
        Args:
            result: ReviewToolResult to add
        """
        self.tool_results.append(result)
    
    def aggregate(self) -> AggregatedReviewResult:
        """
        Aggregate all tool results.
        
        Returns:
            AggregatedReviewResult with combined findings
        """
        aggregated = AggregatedReviewResult(
            scan_time=datetime.now().isoformat()
        )
        
        # Collect tools scanned and failed
        for result in self.tool_results:
            if result.success:
                aggregated.tools_scanned.append(result.tool_name)
            else:
                aggregated.tools_failed.append(result.tool_name)
            
            # Collect findings
            aggregated.findings.extend(result.findings)
        
        # Count total findings
        aggregated.total_findings = len(aggregated.findings)
        
        # Count by severity
        for finding in aggregated.findings:
            severity = finding.severity.value
            aggregated.findings_by_severity[severity] = aggregated.findings_by_severity.get(severity, 0) + 1
        
        # Count by category
        for finding in aggregated.findings:
            category = finding.category.value
            aggregated.findings_by_category[category] = aggregated.findings_by_category.get(category, 0) + 1
        
        # Count by tool
        for finding in aggregated.findings:
            tool = finding.tool
            aggregated.findings_by_tool[tool] = aggregated.findings_by_tool.get(tool, 0) + 1
        
        # Calculate metrics
        aggregated.metrics = self._calculate_metrics()
        
        return aggregated
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate aggregated metrics."""
        metrics = {
            "tools_count": len(self.tool_results),
            "successful_tools": len(self.tool_results),
            "failed_tools": sum(1 for r in self.tool_results if not r.success),
            "total_execution_time": sum(r.execution_time_seconds for r in self.tool_results),
            "average_execution_time": 0.0
        }
        
        # Calculate average execution time
        if metrics["successful_tools"] > 0:
            metrics["average_execution_time"] = (
                metrics["total_execution_time"] / metrics["successful_tools"]
            )
        
        return metrics
    
    def normalize_severity_level(self, tool_name: str) -> bool:
        """
        Normalize severity levels across tools.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if normalization was applied
        """
        normalized = False
        
        for result in self.tool_results:
            if result.tool_name == tool_name:
                for finding in result.findings:
                    old_severity = finding.severity.value
                    
                    # Map severity if needed
                    if old_severity in self.severity_mapping:
                        finding.severity = self.severity_mapping[old_severity]
                        normalized = True
                    
                    # Map category if needed
                    old_category = finding.category.value
                    if old_category in self.category_mapping:
                        finding.category = self.category_mapping[old_category]
        
        return normalized
    
    def deduplicate_findings(
        self,
        similarity_threshold: float = 0.8
    ) -> int:
        """
        Deduplicate findings across tools.
        
        Args:
            similarity_threshold: Threshold for considering findings as duplicates
            
        Returns:
            Number of duplicates removed
        """
        duplicates = 0
        seen_findings = []
        unique_findings = []
        
        for result in self.tool_results:
            for finding in result.findings:
                is_duplicate = False
                
                for seen in seen_findings:
                    if self._are_similar(finding, seen, similarity_threshold):
                        duplicates += 1
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_findings.append(finding)
                    seen_findings.append(finding)
        
        # Update results with unique findings
        for result in self.tool_results:
            result.findings = [f for f in result.findings if f in unique_findings]
        
        return duplicates
    
    def _are_similar(
        self,
        finding1: ReviewFinding,
        finding2: ReviewFinding,
        threshold: float
    ) -> bool:
        """
        Check if two findings are similar.
        
        Args:
            finding1: First finding
            finding2: Second finding
            threshold: Similarity threshold
            
        Returns:
            True if findings are similar
        """
        # Check if they're in the same file and location
        if finding1.file_path == finding2.file_path:
            if finding1.line_number == finding2.line_number:
                return True
        
        # Check title similarity
        title1 = finding1.title.lower()
        title2 = finding2.title.lower()
        
        if title1 == title2:
            return True
        
        # Check if one title contains the other
        if title1 in title2 or title2 in title1:
            return True
        
        # Check rule ID similarity
        if finding1.rule_id and finding2.rule_id:
            if finding1.rule_id == finding2.rule_id:
                return True
        
        return False
    
    def filter_findings(
        self,
        severity: Optional[FindingSeverity] = None,
        category: Optional[FindingCategory] = None,
        tool: Optional[str] = None,
        min_severity: Optional[FindingSeverity] = None
    ) -> List[ReviewFinding]:
        """
        Filter findings by criteria.
        
        Args:
            severity: Filter by severity level
            category: Filter by category
            tool: Filter by tool name
            min_severity: Minimum severity level to include
            
        Returns:
            Filtered list of findings
        """
        filtered = []
        
        for result in self.tool_results:
            for finding in result.findings:
                # Check severity filter
                if severity and finding.severity != severity:
                    continue
                
                if min_severity and self._compare_severity(finding.severity, min_severity) < 0:
                    continue
                
                # Check category filter
                if category and finding.category != category:
                    continue
                
                # Check tool filter
                if tool and finding.tool != tool:
                    continue
                
                filtered.append(finding)
        
        return filtered
    
    def _compare_severity(
        self,
        severity1: FindingSeverity,
        severity2: FindingSeverity
    ) -> int:
        """
        Compare two severity levels.
        
        Args:
            severity1: First severity
            severity2: Second severity
            
        Returns:
            -1 if severity1 < severity2, 0 if equal, 1 if severity1 > severity2
        """
        severity_order = [
            FindingSeverity.INFO,
            FindingSeverity.LOW,
            FindingSeverity.MEDIUM,
            FindingSeverity.HIGH,
            FindingSeverity.CRITICAL
        ]
        
        try:
            idx1 = severity_order.index(severity1)
            idx2 = severity_order.index(severity2)
            return (idx1 > idx2) - (idx1 < idx2)
        except ValueError:
            return 0
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all results.
        
        Returns:
            Summary dictionary
        """
        aggregated = self.aggregate()
        
        return {
            "total_tools": len(self.tool_results),
            "successful_tools": len(aggregated.tools_scanned),
            "failed_tools": len(aggregated.tools_failed),
            "total_findings": aggregated.total_findings,
            "critical_findings": aggregated.findings_by_severity.get("critical", 0),
            "high_findings": aggregated.findings_by_severity.get("high", 0),
            "medium_findings": aggregated.findings_by_severity.get("medium", 0),
            "low_findings": aggregated.findings_by_severity.get("low", 0),
            "info_findings": aggregated.findings_by_severity.get("info", 0),
            "security_findings": aggregated.findings_by_category.get("security", 0),
            "code_quality_findings": aggregated.findings_by_category.get("code_quality", 0),
            "findings_by_tool": aggregated.findings_by_tool,
            "execution_time_seconds": aggregated.metrics.get("total_execution_time", 0)
        }
    
    def export_report(self, output_file: Optional[Path] = None) -> str:
        """
        Export aggregated report.
        
        Args:
            output_file: Optional file to save report
            
        Returns:
            Report content
        """
        aggregated = self.aggregate()
        
        lines = [
            "Code Review Report",
            "=" * 50,
            "",
            f"Scan Time: {aggregated.scan_time}",
            f"Total Tools: {len(self.tool_results)}",
            f"Successful: {len(aggregated.tools_scanned)}",
            f"Failed: {len(aggregated.tools_failed)}",
            f"Total Findings: {aggregated.total_findings}",
            "",
            "Findings by Severity:",
            "-" * 30
        ]
        
        for severity in ["critical", "high", "medium", "low", "info"]:
            count = aggregated.findings_by_severity.get(severity, 0)
            lines.append(f"  {severity.title()}: {count}")
        
        lines.append("")
        lines.append("Findings by Category:")
        lines.append("-" * 30)
        
        for category in ["security", "code_quality", "performance", "maintainability", "style", "documentation", "testing", "complexity", "duplication", "naming"]:
            count = aggregated.findings_by_category.get(category, 0)
            lines.append(f"  {category.replace('_', ' ').title()}: {count}")
        
        lines.append("")
        lines.append("Findings by Tool:")
        lines.append("-" * 30)
        
        for tool, count in aggregated.findings_by_tool.items():
            lines.append(f"  {tool}: {count}")
        
        lines.append("")
        lines.append("Execution Time:")
        lines.append("-" * 30)
        lines.append(f"  Total: {aggregated.metrics.get('total_execution_time', 0):.2f}s")
        lines.append(f"  Average: {aggregated.metrics.get('average_execution_time', 0):.2f}s")
        
        content = "\n".join(lines)
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(content)
            except IOError as e:
                raise IFlowError(
                    f"Failed to export report: {str(e)}",
                    ErrorCode.FILE_WRITE_ERROR
                )
        
        return content


def create_review_aggregator() -> ReviewAggregator:
    """Create a review aggregator instance."""
    return ReviewAggregator()


def aggregate_review_results(
    results: List[ReviewToolResult]
) -> AggregatedReviewResult:
    """
    Aggregate review results.
    
    Args:
        results: List of ReviewToolResult to aggregate
        
    Returns:
        AggregatedReviewResult
    """
    aggregator = ReviewAggregator()
    
    for result in results:
        aggregator.add_result(result)
    
    return aggregator.aggregate()