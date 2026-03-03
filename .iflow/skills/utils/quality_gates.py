"""Quality Gates - Validates that outputs meet quality standards.

This module provides functionality for defining and validating quality
gates that workflow outputs must pass before proceeding.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import (
    IFlowError,
    ValidationError,
    ErrorCode,
    ErrorCategory
)
from .constants import ValidationPatterns


class QualityGate:
    """Represents a single quality gate."""
    
    def __init__(
        self,
        name: str,
        gate_type: str,
        threshold: Any,
        severity: str = "error",
        description: str = ""
    ):
        """
        Initialize a quality gate.
        
        Args:
            name: Name of the quality gate
            gate_type: Type of gate (test_coverage, bug_severity, security, etc.)
            threshold: Threshold value for the gate
            severity: Severity level (error, warning, info)
            description: Description of what the gate checks
        """
        self.name = name
        self.gate_type = gate_type
        self.threshold = threshold
        self.severity = severity
        self.description = description
        self.passed = False
        self.message = ""
        self.details = {}
    
    def evaluate(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Evaluate the quality gate against data.
        
        Args:
            data: Data to evaluate against
            
        Returns:
            Tuple of (passed, message, details)
        """
        if self.gate_type == "test_coverage":
            return self._evaluate_test_coverage(data)
        elif self.gate_type == "bug_severity":
            return self._evaluate_bug_severity(data)
        elif self.gate_type == "security_scan":
            return self._evaluate_security_scan(data)
        elif self.gate_type == "documentation":
            return self._evaluate_documentation(data)
        elif self.gate_type == "lint_errors":
            return self._evaluate_lint_errors(data)
        elif self.gate_type == "security_vulnerabilities":
            return self._evaluate_security_vulnerabilities(data)
        elif self.gate_type == "regression_test":
            return self._evaluate_regression_test(data)
        else:
            return True, f"Unknown gate type: {self.gate_type}", {}
    
    def _evaluate_test_coverage(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Evaluate test coverage gate."""
        coverage = data.get("test_coverage", 0)
        min_coverage = self.threshold
        
        if coverage >= min_coverage:
            self.passed = True
            self.message = f"Test coverage {coverage}% meets threshold {min_coverage}%"
            return True, self.message, {"coverage": coverage, "threshold": min_coverage}
        else:
            self.passed = False
            self.message = f"Test coverage {coverage}% below threshold {min_coverage}%"
            return False, self.message, {"coverage": coverage, "threshold": min_coverage}
    
    def _evaluate_bug_severity(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Evaluate bug severity gate."""
        bugs = data.get("bugs", [])
        max_allowed = self.threshold
        
        severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        
        max_found = 0
        for bug in bugs:
            severity = bug.get("severity", "low")
            severity_level = severity_order.get(severity, 0)
            if severity_level > max_found:
                max_found = severity_level
        
        if max_found <= severity_order.get(max_allowed, 0):
            self.passed = True
            self.message = f"Maximum bug severity within allowed level: {max_allowed}"
            return True, self.message, {"max_severity": max_found, "allowed": max_allowed}
        else:
            self.passed = False
            self.message = f"Bug severity {max_found} exceeds allowed level {max_allowed}"
            return False, self.message, {"max_severity": max_found, "allowed": max_allowed}
    
    def _evaluate_security_scan(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Evaluate security scan gate."""
        required = self.threshold
        scan_performed = data.get("security_scan_performed", False)
        scan_passed = data.get("security_scan_passed", False)
        
        if required:
            if not scan_performed:
                self.passed = False
                self.message = "Security scan not performed"
                return False, self.message, {"required": True, "performed": False}
            elif not scan_passed:
                self.passed = False
                self.message = "Security scan failed"
                return False, self.message, {"required": True, "performed": True, "passed": False}
        
        self.passed = True
        self.message = "Security scan requirements met"
        return True, self.message, {"required": required, "performed": scan_performed}
    
    def _evaluate_documentation(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Evaluate documentation gate."""
        required = self.threshold
        docs_complete = data.get("documentation_complete", False)
        
        if required and not docs_complete:
            self.passed = False
            self.message = "Documentation incomplete"
            return False, self.message, {"required": True, "complete": docs_complete}
        
        self.passed = True
        self.message = "Documentation requirements met"
        return True, self.message, {"required": required, "complete": docs_complete}
    
    def _evaluate_lint_errors(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Evaluate lint errors gate."""
        lint_errors = data.get("lint_errors", 0)
        max_allowed = self.threshold
        
        if lint_errors <= max_allowed:
            self.passed = True
            self.message = f"Lint errors {lint_errors} within allowed limit {max_allowed}"
            return True, self.message, {"errors": lint_errors, "allowed": max_allowed}
        else:
            self.passed = False
            self.message = f"Lint errors {lint_errors} exceed allowed limit {max_allowed}"
            return False, self.message, {"errors": lint_errors, "allowed": max_allowed}
    
    def _evaluate_security_vulnerabilities(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Evaluate security vulnerabilities gate."""
        vulnerabilities = data.get("security_vulnerabilities", [])
        max_allowed = self.threshold
        
        if len(vulnerabilities) <= max_allowed:
            self.passed = True
            self.message = f"Security vulnerabilities {len(vulnerabilities)} within allowed limit {max_allowed}"
            return True, self.message, {"count": len(vulnerabilities), "allowed": max_allowed}
        else:
            self.passed = False
            self.message = f"Security vulnerabilities {len(vulnerabilities)} exceed allowed limit {max_allowed}"
            return False, self.message, {"count": len(vulnerabilities), "allowed": max_allowed}
    
    def _evaluate_regression_test(self, data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Evaluate regression test gate."""
        required = self.threshold
        tests_passed = data.get("regression_tests_passed", False)
        
        if required and not tests_passed:
            self.passed = False
            self.message = "Regression tests not passed"
            return False, self.message, {"required": True, "passed": tests_passed}
        
        self.passed = True
        self.message = "Regression test requirements met"
        return True, self.message, {"required": required, "passed": tests_passed}


class QualityGateEvaluator:
    """Evaluates quality gates against workflow outputs."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the quality gate evaluator.
        
        Args:
            config: Quality gate configuration
        """
        self.config = config or {}
        self.gates: List[QualityGate] = []
        self._load_gates_from_config()
    
    def _load_gates_from_config(self):
        """Load quality gates from configuration."""
        quality_gates_config = self.config.get("quality_gates", {})
        
        if quality_gates_config.get("test_coverage_threshold") is not None:
            self.gates.append(QualityGate(
                name="test_coverage",
                gate_type="test_coverage",
                threshold=quality_gates_config["test_coverage_threshold"],
                severity="error",
                description="Minimum test coverage percentage"
            ))
        
        if quality_gates_config.get("max_bug_severity") is not None:
            self.gates.append(QualityGate(
                name="bug_severity",
                gate_type="bug_severity",
                threshold=quality_gates_config["max_bug_severity"],
                severity="error",
                description="Maximum allowed bug severity"
            ))
        
        if quality_gates_config.get("security_scan_required") is not None:
            self.gates.append(QualityGate(
                name="security_scan",
                gate_type="security_scan",
                threshold=quality_gates_config["security_scan_required"],
                severity="error",
                description="Security scan requirement"
            ))
        
        if quality_gates_config.get("documentation_required") is not None:
            self.gates.append(QualityGate(
                name="documentation",
                gate_type="documentation",
                threshold=quality_gates_config["documentation_required"],
                severity="warning",
                description="Documentation requirement"
            ))
        
        if quality_gates_config.get("lint_errors_allowed") is not None:
            self.gates.append(QualityGate(
                name="lint_errors",
                gate_type="lint_errors",
                threshold=quality_gates_config["lint_errors_allowed"],
                severity="warning",
                description="Maximum allowed lint errors"
            ))
        
        if quality_gates_config.get("security_vulnerabilities_allowed") is not None:
            self.gates.append(QualityGate(
                name="security_vulnerabilities",
                gate_type="security_vulnerabilities",
                threshold=quality_gates_config["security_vulnerabilities_allowed"],
                severity="error",
                description="Maximum allowed security vulnerabilities"
            ))
        
        if quality_gates_config.get("regression_test_required") is not None:
            self.gates.append(QualityGate(
                name="regression_test",
                gate_type="regression_test",
                threshold=quality_gates_config["regression_test_required"],
                severity="error",
                description="Regression test requirement"
            ))
    
    def add_gate(self, gate: QualityGate):
        """Add a custom quality gate."""
        self.gates.append(gate)
    
    def evaluate(self, data: Dict[str, Any]) -> Tuple[int, str, List[Dict[str, Any]]]:
        """
        Evaluate all quality gates against data.
        
        Args:
            data: Data to evaluate against
            
        Returns:
            Tuple of (exit_code, output_message, results)
        """
        results = []
        all_passed = True
        error_count = 0
        warning_count = 0
        
        for gate in self.gates:
            passed, message, details = gate.evaluate(data)
            
            result = {
                "name": gate.name,
                "type": gate.gate_type,
                "passed": passed,
                "severity": gate.severity,
                "message": message,
                "description": gate.description,
                "details": details
            }
            
            results.append(result)
            
            if not passed:
                if gate.severity == "error":
                    all_passed = False
                    error_count += 1
                elif gate.severity == "warning":
                    warning_count += 1
        
        # Generate summary message
        if all_passed:
            summary = f"All {len(self.gates)} quality gates passed"
            exit_code = 0
        else:
            summary_parts = []
            if error_count > 0:
                summary_parts.append(f"{error_count} error(s)")
            if warning_count > 0:
                summary_parts.append(f"{warning_count} warning(s)")
            summary = f"Quality gates failed: {', '.join(summary_parts)}"
            exit_code = 1 if error_count > 0 else 0
        
        return exit_code, summary, results
    
    def get_gate_report(self, results: List[Dict[str, Any]]) -> str:
        """
        Generate a formatted report of quality gate results.
        
        Args:
            results: Quality gate evaluation results
            
        Returns:
            Formatted report string
        """
        lines = ["Quality Gate Report", "=" * 50]
        
        for result in results:
            status_icon = "✓" if result["passed"] else "✗"
            severity_icon = {"error": "!", "warning": "⚠", "info": "i"}.get(result["severity"], "")
            
            lines.append(f"\n{status_icon} {result['name']}")
            lines.append(f"  Type: {result['type']}")
            lines.append(f"  Status: {'PASSED' if result['passed'] else 'FAILED'}")
            lines.append(f"  Severity: {result['severity']} {severity_icon}")
            lines.append(f"  Message: {result['message']}")
            
            if result["details"]:
                lines.append(f"  Details: {json.dumps(result['details'], indent=6)}")
            
            if result["description"]:
                lines.append(f"  Description: {result['description']}")
        
        return "\n".join(lines)
    
    def save_report(self, results: List[Dict[str, Any]], output_file: Path) -> Tuple[int, str]:
        """
        Save quality gate report to file.
        
        Args:
            results: Quality gate evaluation results
            output_file: Path to save the report
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        try:
            report_data = {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_gates": len(results),
                    "passed": sum(1 for r in results if r["passed"]),
                    "failed": sum(1 for r in results if not r["passed"]),
                    "errors": sum(1 for r in results if not r["passed"] and r["severity"] == "error"),
                    "warnings": sum(1 for r in results if not r["passed"] and r["severity"] == "warning")
                },
                "gates": results
            }
            
            with open(output_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            return 0, f"Quality gate report saved to {output_file}"
        
        except Exception as e:
            return 1, f"Failed to save report: {str(e)}"


def create_quality_gate_evaluator(config: Optional[Dict[str, Any]] = None) -> QualityGateEvaluator:
    """Create a quality gate evaluator instance."""
    return QualityGateEvaluator(config=config)


def evaluate_quality_gates(
    data: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> Tuple[int, str, List[Dict[str, Any]]]:
    """
    Convenience function to evaluate quality gates.
    
    Args:
        data: Data to evaluate against
        config: Quality gate configuration
        
    Returns:
        Tuple of (exit_code, output_message, results)
    """
    evaluator = create_quality_gate_evaluator(config)
    return evaluator.evaluate(data)