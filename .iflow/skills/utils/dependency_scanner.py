"""Dependency Security Scanner - Scans dependencies for security vulnerabilities.

This module provides functionality for scanning project dependencies
for security vulnerabilities and outdated packages.
"""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .constants import Timeouts


class VulnerabilitySeverity(Enum):
    """Severity levels for vulnerabilities."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class VulnerabilityType(Enum):
    """Types of vulnerabilities."""
    SECURITY = "security"
    LICENSE = "license"
    OUTDATED = "outdated"
    COMPATIBILITY = "compatibility"


@dataclass
class Vulnerability:
    """Represents a vulnerability in a dependency."""
    package_name: str
    installed_version: str
    affected_versions: List[str]
    severity: VulnerabilitySeverity
    vulnerability_type: VulnerabilityType
    cve_id: Optional[str] = None
    description: str = ""
    advisory_url: Optional[str] = None
    patched_versions: List[str] = None
    recommendation: str = ""
    
    def __post_init__(self):
        if self.patched_versions is None:
            self.patched_versions = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert vulnerability to dictionary."""
        return {
            "package_name": self.package_name,
            "installed_version": self.installed_version,
            "affected_versions": self.affected_versions,
            "severity": self.severity.value,
            "type": self.vulnerability_type.value,
            "cve_id": self.cve_id,
            "description": self.description,
            "advisory_url": self.advisory_url,
            "patched_versions": self.patched_versions,
            "recommendation": self.recommendation
        }


class DependencyScanner:
    """Scans dependencies for security vulnerabilities."""
    
    def __init__(
        self,
        repo_root: Path,
        timeout: int = Timeouts.TEST_DEFAULT.value
    ):
        """
        Initialize the dependency scanner.
        
        Args:
            repo_root: Repository root directory
            timeout: Timeout for scanning operations
        """
        self.repo_root = repo_root
        self.timeout = timeout
        self.scan_results: List[Vulnerability] = []
        self.scan_metadata: Dict[str, Any] = {}
    
    def scan_python_dependencies(
        self,
        requirements_file: Optional[Path] = None
    ) -> Tuple[List[Vulnerability], Dict[str, Any]]:
        """
        Scan Python dependencies for vulnerabilities.
        
        Args:
            requirements_file: Path to requirements.txt (uses default if None)
            
        Returns:
            Tuple of (vulnerabilities, metadata)
        """
        if not requirements_file:
            requirements_file = self.repo_root / "requirements.txt"
        
        if not requirements_file.exists():
            return [], {"error": "requirements.txt not found"}
        
        vulnerabilities = []
        
        # Try using pip-audit if available
        try:
            pip_audit_result = self._run_pip_audit(requirements_file)
            vulnerabilities.extend(pip_audit_result)
        except Exception as e:
            pass  # pip-audit not available
        
        # Try using safety if available
        try:
            safety_result = self._run_safety()
            vulnerabilities.extend(safety_result)
        except Exception as e:
            pass  # safety not available
        
        # Check for outdated packages
        try:
            outdated_result = self._check_outdated_packages()
            vulnerabilities.extend(outdated_result)
        except Exception as e:
            pass
        
        self.scan_results = vulnerabilities
        self.scan_metadata = {
            "scan_time": datetime.now().isoformat(),
            "requirements_file": str(requirements_file),
            "total_vulnerabilities": len(vulnerabilities),
            "by_severity": self._count_by_severity(vulnerabilities),
            "by_type": self._count_by_type(vulnerabilities)
        }
        
        return vulnerabilities, self.scan_metadata
    
    def _run_pip_audit(self, requirements_file: Path) -> List[Vulnerability]:
        """Run pip-audit to check for vulnerabilities."""
        vulnerabilities = []
        
        try:
            result = subprocess.run(
                ["pip-audit", "--format", "json", "--requirement", str(requirements_file)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.repo_root
            )
            
            if result.returncode == 0:
                return vulnerabilities
            
            # Parse pip-audit output
            try:
                data = json.loads(result.stdout)
                
                for vuln_data in data.get("dependencies", []):
                    for vuln in vuln_data.get("vulnerabilities", []):
                        vulnerability = Vulnerability(
                            package_name=vuln_data.get("name", ""),
                            installed_version=vuln_data.get("version", ""),
                            affected_versions=vuln.get("affected_versions", []),
                            severity=self._map_pip_audit_severity(vuln.get("severity")),
                            vulnerability_type=VulnerabilityType.SECURITY,
                            cve_id=vuln.get("id"),
                            description=vuln.get("advisory", ""),
                            advisory_url=vuln.get("advisory_url"),
                            patched_versions=vuln.get("fix_versions", []),
                            recommendation=f"Update to {', '.join(vuln.get('fix_versions', []))}"
                        )
                        vulnerabilities.append(vulnerability)
            
            except json.JSONDecodeError:
                pass
        
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return vulnerabilities
    
    def _run_safety(self) -> List[Vulnerability]:
        """Run safety to check for vulnerabilities."""
        vulnerabilities = []
        
        try:
            result = subprocess.run(
                ["safety", "check", "--json"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.repo_root
            )
            
            if result.returncode == 0:
                return vulnerabilities
            
            # Parse safety output
            try:
                data = json.loads(result.stdout)
                
                for vuln_data in data:
                    vulnerability = Vulnerability(
                        package_name=vuln_data.get("package_name", ""),
                        installed_version=vuln_data.get("installed_version", ""),
                        affected_versions=vuln_data.get("affected_versions", []),
                        severity=self._map_safety_severity(vuln_data.get("severity")),
                        vulnerability_type=VulnerabilityType.SECURITY,
                        cve_id=vuln_data.get("id"),
                        description=vuln_data.get("advisory", ""),
                        advisory_url=vuln_data.get("advisory"),
                        patched_versions=vuln_data.get("fixed_versions", []),
                        recommendation=f"Update to {', '.join(vuln_data.get('fixed_versions', []))}"
                    )
                    vulnerabilities.append(vulnerability)
            
            except json.JSONDecodeError:
                pass
        
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return vulnerabilities
    
    def _check_outdated_packages(self) -> List[Vulnerability]:
        """Check for outdated packages."""
        vulnerabilities = []
        
        try:
            result = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.repo_root
            )
            
            # Parse pip list output
            try:
                data = json.loads(result.stdout)
                
                for pkg_data in data:
                    vulnerability = Vulnerability(
                        package_name=pkg_data.get("name", ""),
                        installed_version=pkg_data.get("version", ""),
                        affected_versions=[f"<={pkg_data.get('latest_version', '')}"],
                        severity=VulnerabilitySeverity.INFO,
                        vulnerability_type=VulnerabilityType.OUTDATED,
                        description=f"Package is outdated. Latest version: {pkg_data.get('latest_version', '')}",
                        patched_versions=[pkg_data.get("latest_version", "")],
                        recommendation=f"Update to {pkg_data.get('latest_version', '')}"
                    )
                    vulnerabilities.append(vulnerability)
            
            except json.JSONDecodeError:
                pass
        
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return vulnerabilities
    
    def _map_pip_audit_severity(self, severity: str) -> VulnerabilitySeverity:
        """Map pip-audit severity to VulnerabilitySeverity."""
        severity_map = {
            "critical": VulnerabilitySeverity.CRITICAL,
            "high": VulnerabilitySeverity.HIGH,
            "medium": VulnerabilitySeverity.MEDIUM,
            "low": VulnerabilitySeverity.LOW
        }
        return severity_map.get(severity.lower(), VulnerabilitySeverity.MEDIUM)
    
    def _map_safety_severity(self, severity: str) -> VulnerabilitySeverity:
        """Map safety severity to VulnerabilitySeverity."""
        severity_map = {
            "critical": VulnerabilitySeverity.CRITICAL,
            "high": VulnerabilitySeverity.HIGH,
            "medium": VulnerabilitySeverity.MEDIUM,
            "low": VulnerabilitySeverity.LOW
        }
        return severity_map.get(severity.lower(), VulnerabilitySeverity.MEDIUM)
    
    def _count_by_severity(self, vulnerabilities: List[Vulnerability]) -> Dict[str, int]:
        """Count vulnerabilities by severity."""
        counts = {}
        for vuln in vulnerabilities:
            severity = vuln.severity.value
            counts[severity] = counts.get(severity, 0) + 1
        return counts
    
    def _count_by_type(self, vulnerabilities: List[Vulnerability]) -> Dict[str, int]:
        """Count vulnerabilities by type."""
        counts = {}
        for vuln in vulnerabilities:
            vtype = vuln.vulnerability_type.value
            counts[vtype] = counts.get(vtype, 0) + 1
        return counts
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate a security scan report.
        
        Returns:
            Report dictionary
        """
        critical_vulns = [v for v in self.scan_results if v.severity == VulnerabilitySeverity.CRITICAL]
        high_vulns = [v for v in self.scan_results if v.severity == VulnerabilitySeverity.HIGH]
        
        return {
            "scan_time": self.scan_metadata.get("scan_time"),
            "total_vulnerabilities": len(self.scan_results),
            "critical_count": len(critical_vulns),
            "high_count": len(high_vulns),
            "medium_count": len([v for v in self.scan_results if v.severity == VulnerabilitySeverity.MEDIUM]),
            "low_count": len([v for v in self.scan_results if v.severity == VulnerabilitySeverity.LOW]),
            "by_severity": self.scan_metadata.get("by_severity", {}),
            "by_type": self.scan_metadata.get("by_type", {}),
            "critical_vulnerabilities": [v.to_dict() for v in critical_vulns],
            "high_vulnerabilities": [v.to_dict() for v in high_vulns],
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on scan results."""
        recommendations = []
        
        critical_vulns = [v for v in self.scan_results if v.severity == VulnerabilitySeverity.CRITICAL]
        high_vulns = [v for v in self.scan_results if v.severity == VulnerabilitySeverity.HIGH]
        
        if critical_vulns:
            recommendations.append(
                f"CRITICAL: {len(critical_vulns)} critical vulnerabilities found. "
                "Update immediately."
            )
        
        if high_vulns:
            recommendations.append(
                f"HIGH: {len(high_vulns)} high severity vulnerabilities found. "
                "Update as soon as possible."
            )
        
        # Group by package for update recommendations
        packages_to_update = {}
        for vuln in self.scan_results:
            if vuln.vulnerability_type in [VulnerabilityType.SECURITY, VulnerabilityType.OUTDATED]:
                if vuln.package_name not in packages_to_update:
                    packages_to_update[vuln.package_name] = []
                
                for version in vuln.patched_versions:
                    if version not in packages_to_update[vuln.package_name]:
                        packages_to_update[vuln.package_name].append(version)
        
        if packages_to_update:
            update_list = []
            for pkg, versions in packages_to_update.items():
                if versions:
                    update_list.append(f"{pkg} to {versions[-1]}")
            
            recommendations.append(f"Update packages: {', '.join(update_list[:10])}")
        
        return recommendations
    
    def check_compliance(
        self,
        max_critical: int = 0,
        max_high: int = 0,
        max_medium: int = 5
    ) -> Tuple[bool, List[str]]:
        """
        Check if dependencies meet security compliance standards.
        
        Args:
            max_critical: Maximum allowed critical vulnerabilities
            max_high: Maximum allowed high severity vulnerabilities
            max_medium: Maximum allowed medium severity vulnerabilities
            
        Returns:
            Tuple of (is_compliant, list_of_issues)
        """
        issues = []
        
        critical_count = len([v for v in self.scan_results if v.severity == VulnerabilitySeverity.CRITICAL])
        high_count = len([v for v in self.scan_results if v.severity == VulnerabilitySeverity.HIGH])
        medium_count = len([v for v in self.scan_results if v.severity == VulnerabilitySeverity.MEDIUM])
        
        if critical_count > max_critical:
            issues.append(
                f"Too many critical vulnerabilities: {critical_count} (max: {max_critical})"
            )
        
        if high_count > max_high:
            issues.append(
                f"Too many high severity vulnerabilities: {high_count} (max: {max_high})"
            )
        
        if medium_count > max_medium:
            issues.append(
                f"Too many medium severity vulnerabilities: {medium_count} (max: {max_medium})"
            )
        
        return len(issues) == 0, issues


def scan_dependencies(
    repo_root: Path,
    requirements_file: Optional[Path] = None
) -> Tuple[List[Vulnerability], Dict[str, Any]]:
    """
    Scan dependencies for vulnerabilities.
    
    Args:
        repo_root: Repository root directory
        requirements_file: Path to requirements.txt
        
    Returns:
        Tuple of (vulnerabilities, metadata)
    """
    scanner = DependencyScanner(repo_root)
    return scanner.scan_python_dependencies(requirements_file)


def check_dependency_compliance(
    repo_root: Path,
    max_critical: int = 0,
    max_high: int = 0,
    max_medium: int = 5
) -> Tuple[bool, List[str]]:
    """
    Check if dependencies meet security compliance standards.
    
    Args:
        repo_root: Repository root directory
        max_critical: Maximum allowed critical vulnerabilities
        max_high: Maximum allowed high severity vulnerabilities
        max_medium: Maximum allowed medium severity vulnerabilities
        
    Returns:
        Tuple of (is_compliant, list_of_issues)
    """
    scanner = DependencyScanner(repo_root)
    scanner.scan_python_dependencies()
    return scanner.check_compliance(max_critical, max_high, max_medium)