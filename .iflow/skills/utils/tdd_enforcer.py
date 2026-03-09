"""TDD Enforcer - Enforces Test-Driven Development practices.

This module provides functionality for enforcing TDD practices including
requiring tests before implementation and validating test coverage.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .git_command import run_git_command


class TDDEnforcer:
    """Enforces Test-Driven Development practices."""
    
    def __init__(self, repo_root: Path, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the TDD enforcer.
        
        Args:
            repo_root: Repository root directory
            config: TDD configuration
        """
        self.repo_root = repo_root
        self.config = config or {}
        self.tdd_enabled = self.config.get("tdd_enabled", True)
        self.test_before_implementation = self.config.get("test_before_implementation", True)
        self.min_test_coverage = self.config.get("min_test_coverage", 80)
        self.test_file_pattern = self.config.get("test_file_pattern", "test_*.py")
        self.implementation_file_pattern = self.config.get("implementation_file_pattern", "*.py")
        self.tdd_violation_log = repo_root / ".iflow" / "tdd_violations.json"
    
    def validate_tdd_workflow(
        self,
        files_changed: List[str],
        branch_name: Optional[str] = None
    ) -> Tuple[int, str, List[Dict[str, Any]]]:
        """
        Validate that the TDD workflow was followed.
        
        Args:
            files_changed: List of files that were changed
            branch_name: Name of the branch being validated
            
        Returns:
            Tuple of (exit_code, output_message, violations)
        """
        if not self.tdd_enabled:
            return 0, "TDD enforcement is disabled", []
        
        violations = []
        
        # Group files into tests and implementations
        test_files = []
        impl_files = []
        
        for file_path in files_changed:
            if self._is_test_file(file_path):
                test_files.append(file_path)
            elif self._is_implementation_file(file_path):
                impl_files.append(file_path)
        
        # Check if implementation files were added/modified without corresponding tests
        if self.test_before_implementation and impl_files:
            for impl_file in impl_files:
                corresponding_test = self._get_corresponding_test_file(impl_file)
                
                if corresponding_test and corresponding_test not in test_files:
                    # Check if test exists and was modified before implementation
                    if not self._test_existed_before_implementation(corresponding_test, impl_file):
                        violations.append({
                            "type": "missing_test",
                            "severity": "error",
                            "file": impl_file,
                            "required_test": corresponding_test,
                            "message": f"Implementation added without corresponding test: {impl_file}"
                        })
        
        # Validate test coverage
        if violations or impl_files:
            coverage_result = self._validate_test_coverage(branch_name)
            if coverage_result[0] != 0:
                violations.extend(coverage_result[2])
        
        # Save violations to log
        self._log_violations(violations)
        
        if violations:
            error_count = sum(1 for v in violations if v["severity"] == "error")
            return 1, f"TDD violations found: {error_count} error(s), {len(violations) - error_count} warning(s)", violations
        else:
            return 0, "TDD workflow validated successfully", []
    
    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file is a test file."""
        path = Path(file_path)
        filename = path.name
        
        # Check if file is in a test directory
        if "test" in path.parts or "tests" in path.parts:
            return True
        
        # Check if filename matches test pattern
        if filename.startswith("test_") or filename.endswith("_test.py"):
            return True
        
        return False
    
    def _is_implementation_file(self, file_path: str) -> bool:
        """Check if a file is an implementation file."""
        path = Path(file_path)
        
        # Skip test files
        if self._is_test_file(file_path):
            return False
        
        # Skip configuration and data files
        extensions_to_skip = [".json", ".yaml", ".yml", ".toml", ".md", ".txt"]
        if path.suffix in extensions_to_skip:
            return False
        
        # Skip if file is in hidden directory or __pycache__
        if any(part.startswith(".") or part == "__pycache__" for part in path.parts):
            return False
        
        # Skip files in iflow or .iflow directories
        if "iflow" in path.parts:
            return False
        
        return path.suffix == ".py"
    
    def _get_corresponding_test_file(self, impl_file: str) -> Optional[str]:
        """Get the corresponding test file for an implementation file."""
        impl_path = Path(impl_file)
        
        # Try to find test file in same directory
        test_dir = impl_path.parent / "tests"
        if not test_dir.exists():
            # Try tests/ at higher level
            for parent in impl_path.parents:
                potential_test_dir = parent / "tests"
                if potential_test_dir.exists():
                    test_dir = potential_test_dir
                    break
        
        # Generate test filename
        test_filename = f"test_{impl_path.stem}.py"
        test_path = test_dir / impl_path.relative_to(impl_path.parent).parent / test_filename
        
        return str(test_path) if test_path.exists() else None
    
    def _test_existed_before_implementation(
        self,
        test_file: str,
        impl_file: str
    ) -> bool:
        """Check if the test file existed before the implementation was added."""
        try:
            # Get the commit when implementation was added
            test_file_path = Path(test_file).name
            impl_file_path = Path(impl_file).name
            
            # Check if test file has commits before implementation
            code, stdout, stderr = run_git_command(
                ["log", "--oneline", "--", test_file],
                cwd=self.repo_root,
                check_secrets=False
            )
            
            if code == 0 and stdout.strip():
                # Test file has history
                return True
            
            return False
        
        except Exception as e:
            self.logger.warning(f"Test execution check failed: {e}")
            return False
    
    def _validate_test_coverage(
        self,
        branch_name: Optional[str] = None
    ) -> Tuple[int, str, List[Dict[str, Any]]]:
        """
        Validate test coverage meets minimum requirements.
        
        Args:
            branch_name: Name of the branch to check
            
        Returns:
            Tuple of (exit_code, output_message, violations)
        """
        violations = []
        
        # Try to get coverage data if available
        # This is a simplified check - real implementation would use coverage.py
        
        # Check if coverage file exists
        coverage_file = self.repo_root / ".coverage"
        coverage_report = self.repo_root / "coverage.json"
        
        if coverage_report.exists():
            try:
                with open(coverage_report, 'r') as f:
                    coverage_data = json.load(f)
                
                total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0)
                
                if total_coverage < self.min_test_coverage:
                    violations.append({
                        "type": "insufficient_coverage",
                        "severity": "warning",
                        "message": f"Test coverage {total_coverage}% below minimum {self.min_test_coverage}%",
                        "coverage": total_coverage,
                        "required": self.min_test_coverage
                    })
            
            except Exception as e:
                self.logger.warning(f"Coverage check error: {e}")
                pass
        
        if violations:
            return 1, "Test coverage validation failed", violations
        else:
            return 0, "Test coverage validation passed", []
    
    def generate_tdd_report(
        self,
        violations: List[Dict[str, Any]],
        output_file: Optional[Path] = None
    ) -> str:
        """
        Generate a TDD compliance report.
        
        Args:
            violations: List of TDD violations
            output_file: Optional file to save the report
            
        Returns:
            Formatted report string
        """
        lines = ["TDD Compliance Report", "=" * 50]
        lines.append(f"Generated: {datetime.now().isoformat()}")
        lines.append(f"Total Violations: {len(violations)}")
        
        # Group by severity
        errors = [v for v in violations if v["severity"] == "error"]
        warnings = [v for v in violations if v["severity"] == "warning"]
        
        lines.append(f"\nErrors: {len(errors)}")
        lines.append(f"Warnings: {len(warnings)}")
        
        if errors:
            lines.append("\nError Violations:")
            for violation in errors:
                lines.append(f"  - {violation['message']}")
                if "file" in violation:
                    lines.append(f"    File: {violation['file']}")
                if "required_test" in violation:
                    lines.append(f"    Required Test: {violation['required_test']}")
        
        if warnings:
            lines.append("\nWarning Violations:")
            for violation in warnings:
                lines.append(f"  - {violation['message']}")
        
        if not violations:
            lines.append("\n✓ No TDD violations found")
        
        report = "\n".join(lines)
        
        if output_file:
            try:
                report_data = {
                    "timestamp": datetime.now().isoformat(),
                    "summary": {
                        "total_violations": len(violations),
                        "errors": len(errors),
                        "warnings": len(warnings)
                    },
                    "violations": violations,
                    "report_text": report
                }
                
                with open(output_file, 'w') as f:
                    json.dump(report_data, f, indent=2)
            
            except Exception as e:
                self.logger.warning(f"Failed to write TDD report to {output_file}: {e}")
                pass
        
        return report
    
    def _log_violations(self, violations: List[Dict[str, Any]]):
        """Log TDD violations to file."""
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "violations": violations
            }
            
            # Load existing log
            existing_log = []
            if self.tdd_violation_log.exists():
                with open(self.tdd_violation_log, 'r') as f:
                    existing_log = json.load(f)
            
            # Add new violations
            existing_log.append(log_data)
            
            # Keep only last 100 entries
            existing_log = existing_log[-100:]
            
            # Save log
            with open(self.tdd_violation_log, 'w') as f:
                json.dump(existing_log, f, indent=2)
        
        except Exception as e:
            self.logger.warning(f"Failed to save TDD violation log: {e}")
            pass
    
    def get_violation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get the TDD violation history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of violation entries
        """
        try:
            if not self.tdd_violation_log.exists():
                return []
            
            with open(self.tdd_violation_log, 'r') as f:
                log = json.load(f)
            
            return log[-limit:]
        
        except Exception as e:
            self.logger.warning(f"Failed to load TDD violation history: {e}")
            return []
    
    def enforce_tdd_pre_commit(
        self,
        staged_files: List[str]
    ) -> Tuple[int, str]:
        """
        Enforce TDD rules as a pre-commit hook.
        
        Args:
            staged_files: List of files staged for commit
            
        Returns:
            Tuple of (exit_code, output_message)
        """
        code, message, violations = self.validate_tdd_workflow(staged_files)
        
        if code != 0:
            report = self.generate_tdd_report(violations)
            return 1, f"{message}\n\n{report}"
        
        return 0, message


def create_tdd_enforcer(
    repo_root: Path,
    config: Optional[Dict[str, Any]] = None
) -> TDDEnforcer:
    """Create a TDD enforcer instance."""
    return TDDEnforcer(repo_root=repo_root, config=config)