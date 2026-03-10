"""Review Tool Integration - Integrates auto-review tools (SonarQube, Snyk).

This module provides functionality for integrating with various code review and
security scanning tools such as SonarQube, Snyk, ESLint, Pylint, etc.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import subprocess
import re

from .exceptions import (
    IFlowError,
    ErrorCode
)
from .constants import Timeouts


class ReviewTool:
    """Base class for review tools."""
    
    def __init__(self, name: str, version: Optional[str] = None):
        """
        Initialize a review tool.
        
        Args:
            name: Name of the tool
            version: Optional version requirement
        """
        self.name = name
        self.version = version
        self.installed = False
        self.tool_version = None
        self.tool_name = name  # For backward compatibility
    
    def check_installed(self) -> bool:
        """Check if the tool is installed."""
        try:
            result = subprocess.run(
                [self.name, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            self.installed = result.returncode == 0
            if self.installed:
                # Extract version from output
                output = result.stdout or result.stderr
                version_match = re.search(r'(\d+\.\d+\.?\d*)', output)
                self.tool_version = version_match.group(1) if version_match else "unknown"
            return self.installed
        except Exception as e:
            # Logger not available in base class, using print for debugging
            print(f"Warning: Failed to check if {self.tool_name} is installed: {e}")
            self.installed = False
            return False
    
    def run_scan(self, path: Path, **kwargs) -> Dict[str, Any]:
        """Run a scan. Override in subclass."""
        raise NotImplementedError(f"{self.__class__.__name__}.run_scan() must be implemented by subclass")


class SonarQubeScanner(ReviewTool):
    """SonarQube code quality scanner."""
    
    def __init__(self, host_url: str, token: str):
        """
        Initialize SonarQube scanner.
        
        Args:
            host_url: SonarQube server URL
            token: SonarQube authentication token
        """
        super().__init__("sonar-scanner")
        self.host_url = host_url
        self.token = token
        self.check_installed()
    
    def run_scan(
        self,
        project_path: Path,
        project_key: str,
        sources: str = ".",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run SonarQube scan.
        
        Args:
            project_path: Path to project directory
            project_key: SonarQube project key
            sources: Source directory to scan
            **kwargs: Additional sonar-scanner parameters
            
        Returns:
            Scan results dictionary
        """
        if not self.installed:
            return {
                "success": False,
                "error": f"{self.name} is not installed",
                "issues": []
            }
        
        try:
            # Build sonar-scanner command
            cmd = [
                self.name,
                f"-Dsonar.host.url={self.host_url}",
                f"-Dsonar.login={self.token}",
                f"-Dsonar.projectKey={project_key}",
                f"-Dsonar.sources={sources}",
                f"-Dsonar.projectBaseDir={project_path}"
            ]
            
            # Add additional parameters
            for key, value in kwargs.items():
                cmd.append(f"-Dsonar.{key}={value}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=Timeouts.SCAN_TIMEOUT.value,
                cwd=project_path
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "issues": self._parse_issues(result.stdout)
            }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "SonarQube scan timed out",
                "issues": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "issues": []
            }
    
    def _parse_issues(self, output: str) -> List[Dict[str, Any]]:
        """Parse issues from SonarQube output."""
        issues = []
        # SonarQube issues are typically retrieved via API
        # This is a simplified parser for command output
        return issues
    
    def get_quality_gate(self, project_key: str) -> Dict[str, Any]:
        """
        Get quality gate status from SonarQube API.
        
        Args:
            project_key: SonarQube project key
            
        Returns:
            Quality gate status
        """
        # This would require HTTP requests to SonarQube API
        # Simplified implementation
        return {
            "status": "UNKNOWN",
            "conditions": []
        }


class SnykScanner(ReviewTool):
    """Snyk security scanner."""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize Snyk scanner.
        
        Args:
            token: Snyk API token (optional)
        """
        super().__init__("snyk")
        self.token = token
        self.check_installed()
    
    def run_scan(
        self,
        target_path: Path,
        scan_type: str = "code",
        severity: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run Snyk scan.
        
        Args:
            target_path: Path to scan
            scan_type: Type of scan ('code', 'dependency', 'container', 'iac')
            severity: Minimum severity level
            **kwargs: Additional Snyk parameters
            
        Returns:
            Scan results dictionary
        """
        if not self.installed:
            return {
                "success": False,
                "error": f"{self.name} is not installed",
                "vulnerabilities": []
            }
        
        try:
            # Build snyk command
            cmd = [self.name]
            
            if scan_type == "code":
                cmd.extend(["code", "test"])
            elif scan_type == "dependency":
                cmd.extend(["test"])
            elif scan_type == "container":
                cmd.extend(["container", "test"])
            elif scan_type == "iac":
                cmd.extend(["iac", "test"])
            
            cmd.append(str(target_path))
            
            # Add options
            if severity:
                cmd.extend(["--severity-threshold", severity])
            
            if self.token:
                cmd.extend(["--auth", self.token])
            
            cmd.append("--json")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=Timeouts.SCAN_TIMEOUT.value,
                cwd=target_path.parent
            )
            
            if result.returncode == 0:
                # Parse JSON output
                try:
                    data = json.loads(result.stdout)
                    return {
                        "success": True,
                        "data": data,
                        "vulnerabilities": self._parse_vulnerabilities(data)
                    }
                except json.JSONDecodeError:
                    return {
                        "success": True,
                        "output": result.stdout,
                        "vulnerabilities": []
                    }
            else:
                return {
                    "success": False,
                    "error": result.stderr,
                    "vulnerabilities": []
                }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Snyk scan timed out",
                "vulnerabilities": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "vulnerabilities": []
            }
    
    def _parse_vulnerabilities(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse vulnerabilities from Snyk output."""
        vulnerabilities = []
        
        if "vulnerabilities" in data:
            for vuln in data["vulnerabilities"]:
                vulnerabilities.append({
                    "id": vuln.get("id", ""),
                    "title": vuln.get("title", ""),
                    "severity": vuln.get("severity", ""),
                    "cvssScore": vuln.get("cvssScore", 0),
                    "cvssVector": vuln.get("cvssVector", ""),
                    "description": vuln.get("description", ""),
                    "references": vuln.get("references", []),
                    "fixedIn": vuln.get("fixedIn", [])
                })
        
        return vulnerabilities
    
    def get_license_compliance(self, target_path: Path) -> Dict[str, Any]:
        """
        Check license compliance.
        
        Args:
            target_path: Path to check
            
        Returns:
            License compliance results
        """
        if not self.installed:
            return {
                "success": False,
                "error": f"{self.name} is not installed",
                "licenses": []
            }
        
        try:
            cmd = [self.name, "test", str(target_path), "--json", "--license"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=Timeouts.SCAN_TIMEOUT.value
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    "success": True,
                    "licenses": data.get("licenses", [])
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class ESLintScanner(ReviewTool):
    """ESLint JavaScript/TypeScript linter."""
    
    def __init__(self):
        """Initialize ESLint scanner."""
        super().__init__("eslint")
        self.check_installed()
    
    def run_scan(
        self,
        target_path: Path,
        config_file: Optional[Path] = None,
        format: str = "json",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run ESLint scan.
        
        Args:
            target_path: Path to scan
            config_file: Path to ESLint config file
            format: Output format ('json', 'stylish', 'compact')
            **kwargs: Additional ESLint parameters
            
        Returns:
            Scan results dictionary
        """
        if not self.installed:
            return {
                "success": False,
                "error": f"{self.name} is not installed",
                "issues": []
            }
        
        try:
            cmd = [self.name]
            
            if config_file:
                cmd.extend(["--config", str(config_file)])
            
            cmd.extend(["--format", format, str(target_path)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=Timeouts.LINT_TIMEOUT.value
            )
            
            if format == "json":
                try:
                    issues = json.loads(result.stdout)
                    return {
                        "success": True,
                        "issues": issues,
                        "summary": self._generate_summary(issues)
                    }
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "Failed to parse JSON output"
                    }
            else:
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr if result.returncode != 0 else None
                }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "ESLint scan timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_summary(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Generate summary of issues."""
        summary = {"error": 0, "warning": 0}
        for issue in issues:
            severity = issue.get("severity", 0)
            if severity == 2:
                summary["error"] += 1
            elif severity == 1:
                summary["warning"] += 1
        return summary


class PylintScanner(ReviewTool):
    """Pylint Python linter."""
    
    def __init__(self):
        """Initialize Pylint scanner."""
        super().__init__("pylint")
        self.check_installed()
    
    def run_scan(
        self,
        target_path: Path,
        config_file: Optional[Path] = None,
        output_format: str = "json",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run Pylint scan.
        
        Args:
            target_path: Path to scan
            config_file: Path to Pylint config file
            output_format: Output format ('json', 'text')
            **kwargs: Additional Pylint parameters
            
        Returns:
            Scan results dictionary
        """
        if not self.installed:
            return {
                "success": False,
                "error": f"{self.name} is not installed",
                "issues": []
            }
        
        try:
            cmd = [self.name]
            
            if config_file:
                cmd.extend(["--rcfile", str(config_file)])
            
            cmd.extend(["--output-format", output_format, str(target_path)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=Timeouts.LINT_TIMEOUT.value
            )
            
            if output_format == "json":
                try:
                    issues = json.loads(result.stdout)
                    return {
                        "success": True,
                        "issues": issues,
                        "summary": self._generate_summary(issues)
                    }
                except json.JSONDecodeError:
                    return {
                        "success": False,
                        "error": "Failed to parse JSON output"
                    }
            else:
                return {
                    "success": result.returncode == 0,
                    "output": result.stdout,
                    "error": result.stderr if result.returncode != 0 else None
                }
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Pylint scan timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_summary(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """Generate summary of issues."""
        summary = {
            "fatal": 0,
            "error": 0,
            "warning": 0,
            "convention": 0,
            "refactor": 0,
            "info": 0
        }
        for issue in issues:
            msg_type = issue.get("type", "")
            if msg_type in summary:
                summary[msg_type] += 1
        return summary


class ReviewToolIntegration:
    """Manages integration with multiple review tools."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize review tool integration.
        
        Args:
            config: Configuration dictionary for tools
        """
        self.config = config or {}
        self.tools: Dict[str, ReviewTool] = {}
        self._initialize_tools()
    
    def _initialize_tools(self):
        """Initialize configured review tools."""
        # Initialize SonarQube if configured
        if "sonarqube" in self.config:
            sq_config = self.config["sonarqube"]
            if sq_config.get("enabled", False):
                self.tools["sonarqube"] = SonarQubeScanner(
                    host_url=sq_config.get("host_url", ""),
                    token=sq_config.get("token", "")
                )
        
        # Initialize Snyk if configured
        if "snyk" in self.config:
            snyk_config = self.config["snyk"]
            if snyk_config.get("enabled", False):
                self.tools["snyk"] = SnykScanner(
                    token=snyk_config.get("token")
                )
        
        # Initialize ESLint if enabled
        if "eslint" in self.config and self.config["eslint"].get("enabled", False):
            self.tools["eslint"] = ESLintScanner()
        
        # Initialize Pylint if enabled
        if "pylint" in self.config and self.config["pylint"].get("enabled", False):
            self.tools["pylint"] = PylintScanner()
    
    def run_all_scans(
        self,
        project_path: Path,
        tool_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run scans with all configured tools.
        
        Args:
            project_path: Path to project
            tool_names: Optional list of specific tools to run
            
        Returns:
            Combined results from all scans
        """
        results = {}
        tools_to_run = tool_names if tool_names else list(self.tools.keys())
        
        for tool_name in tools_to_run:
            if tool_name in self.tools:
                tool = self.tools[tool_name]
                if tool.installed:
                    results[tool_name] = tool.run_scan(project_path)
                else:
                    results[tool_name] = {
                        "success": False,
                        "error": f"{tool_name} is not installed"
                    }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "project_path": str(project_path),
            "results": results,
            "summary": self._generate_summary(results)
        }
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of all scan results."""
        summary = {
            "total_tools": len(results),
            "successful_scans": 0,
            "failed_scans": 0,
            "total_issues": 0,
            "critical_issues": 0,
            "high_severity_issues": 0
        }
        
        for tool_name, result in results.items():
            if result.get("success", False):
                summary["successful_scans"] += 1
            else:
                summary["failed_scans"] += 1
            
            # Count issues
            if "issues" in result:
                summary["total_issues"] += len(result["issues"])
            
            if "vulnerabilities" in result:
                for vuln in result["vulnerabilities"]:
                    severity = vuln.get("severity", "").lower()
                    if severity in ["critical", "high"]:
                        summary["high_severity_issues"] += 1
        
        return summary
    
    def get_tool_status(self) -> Dict[str, Any]:
        """Get status of all configured tools."""
        status = {}
        for name, tool in self.tools.items():
            status[name] = {
                "installed": tool.installed,
                "version": tool.tool_version
            }
        return status
    
    def save_results(self, results: Dict[str, Any], output_file: Path):
        """
        Save scan results to file.
        
        Args:
            results: Scan results dictionary
            output_file: Path to output file
        """
        try:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            raise IFlowError(
                f"Failed to save results: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )


def create_review_integration(config: Optional[Dict[str, Any]] = None) -> ReviewToolIntegration:
    """Create a review tool integration instance."""
    return ReviewToolIntegration(config=config)