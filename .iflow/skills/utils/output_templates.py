"""Output Templates - Provides templates for formatting workflow results.

This module provides reusable templates for formatting and presenting
workflow results, pipeline outputs, and operation status in various formats.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum


class OutputFormat(Enum):
    """Output format types."""
    JSON = "json"
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    TABLE = "table"


class OutputTemplate:
    """Base class for output templates."""
    
    def __init__(self, template_name: str, format: OutputFormat):
        """
        Initialize an output template.
        
        Args:
            template_name: Name of the template
            format: Output format type
        """
        self.template_name = template_name
        self.format = format
    
    def render(self, data: Dict[str, Any]) -> str:
        """
        Render the template with data.
        
        Args:
            data: Data to populate template
            
        Returns:
            Formatted output string
        """
        raise NotImplementedError


class WorkflowResultTemplate(OutputTemplate):
    """Template for workflow operation results."""
    
    def __init__(self, format: OutputFormat = OutputFormat.TEXT):
        """Initialize workflow result template."""
        super().__init__("workflow_result", format)
    
    def render(self, data: Dict[str, Any]) -> str:
        """Render workflow result."""
        operation = data.get("operation", "unknown")
        status = data.get("status", "unknown")
        message = data.get("message", "")
        exit_code = data.get("exit_code", 0)
        duration = data.get("duration_seconds")
        
        if self.format == OutputFormat.JSON:
            return json.dumps(data, indent=2)
        
        elif self.format == OutputFormat.TEXT:
            lines = [
                f"Operation: {operation}",
                f"Status: {status.upper()}",
                f"Exit Code: {exit_code}",
                ""
            ]
            
            if message:
                lines.append(f"Message: {message}")
                lines.append("")
            
            if duration:
                lines.append(f"Duration: {duration:.2f}s")
            
            if "details" in data:
                lines.append("")
                lines.append("Details:")
                for key, value in data["details"].items():
                    lines.append(f"  {key}: {value}")
            
            return "\n".join(lines)
        
        elif self.format == OutputFormat.MARKDOWN:
            status_emoji = "✅" if exit_code == 0 else "❌"
            lines = [
                f"# {status_emoji} {operation.title()} Result",
                "",
                f"**Status:** {status.upper()}",
                f"**Exit Code:** {exit_code}",
                ""
            ]
            
            if message:
                lines.append(f"**Message:** {message}")
                lines.append("")
            
            if duration:
                lines.append(f"**Duration:** {duration:.2f}s")
                lines.append("")
            
            if "details" in data:
                lines.append("## Details")
                lines.append("")
                lines.append("| Key | Value |")
                lines.append("|-----|-------|")
                for key, value in data["details"].items():
                    lines.append(f"| {key} | {value} |")
            
            return "\n".join(lines)
        
        return str(data)


class BranchStatusTemplate(OutputTemplate):
    """Template for branch status output."""
    
    def __init__(self, format: OutputFormat = OutputFormat.TEXT):
        """Initialize branch status template."""
        super().__init__("branch_status", format)
    
    def render(self, data: Dict[str, Any]) -> str:
        """Render branch status."""
        branches = data.get("branches", {})
        current_branch = data.get("current_branch")
        
        if self.format == OutputFormat.JSON:
            return json.dumps(data, indent=2)
        
        elif self.format == OutputFormat.TEXT:
            lines = ["Branch Status", "=" * 50, ""]
            
            if current_branch:
                lines.append(f"Current Branch: {current_branch}")
                lines.append("")
            
            lines.append("Branches:")
            for branch_name, branch_info in branches.items():
                status = branch_info.get("status", "unknown")
                role = branch_info.get("role", "unknown")
                phase = branch_info.get("phase", "-")
                
                current_marker = " (current)" if branch_name == current_branch else ""
                lines.append(f"  {branch_name}{current_marker}")
                lines.append(f"    Status: {status}")
                lines.append(f"    Role: {role}")
                lines.append(f"    Phase: {phase}")
                lines.append("")
            
            return "\n".join(lines)
        
        elif self.format == OutputFormat.TABLE:
            lines = []
            lines.append("| Branch | Status | Role | Phase |")
            lines.append("|--------|--------|------|-------|")
            
            for branch_name, branch_info in branches.items():
                status = branch_info.get("status", "unknown")
                role = branch_info.get("role", "unknown")
                phase = branch_info.get("phase", "-")
                current_marker = "*" if branch_name == current_branch else ""
                
                lines.append(f"| {branch_name}{current_marker} | {status} | {role} | {phase} |")
            
            return "\n".join(lines)
        
        return str(data)


class PhaseProgressTemplate(OutputTemplate):
    """Template for phase progress output."""
    
    def __init__(self, format: OutputFormat = OutputFormat.TEXT):
        """Initialize phase progress template."""
        super().__init__("phase_progress", format)
    
    def render(self, data: Dict[str, Any]) -> str:
        """Render phase progress."""
        phases = data.get("phases", [])
        current_phase = data.get("current_phase")
        workflow_status = data.get("workflow_status", "unknown")
        
        if self.format == OutputFormat.JSON:
            return json.dumps(data, indent=2)
        
        elif self.format == OutputFormat.TEXT:
            lines = ["Workflow Progress", "=" * 50, ""]
            lines.append(f"Status: {workflow_status}")
            lines.append(f"Current Phase: {current_phase}")
            lines.append("")
            lines.append("Phases:")
            
            for i, phase in enumerate(phases):
                phase_name = phase.get("name", f"Phase {i+1}")
                phase_status = phase.get("status", "pending")
                
                # Add status marker
                if phase_status == "complete":
                    marker = "✓"
                elif phase_status == "active":
                    marker = "→"
                elif phase_status == "blocked":
                    marker = "✗"
                else:
                    marker = "○"
                
                current_marker = " (current)" if phase_name == current_phase else ""
                lines.append(f"  {marker} {phase_name}{current_marker} - {phase_status}")
            
            return "\n".join(lines)
        
        elif self.format == OutputFormat.MARKDOWN:
            status_emoji = {
                "complete": "✅",
                "active": "🔄",
                "blocked": "🚫",
                "pending": "⏳"
            }
            
            lines = [
                f"# Workflow Progress",
                "",
                f"**Status:** {workflow_status}",
                f"**Current Phase:** {current_phase}",
                "",
                "## Phases",
                ""
            ]
            
            for phase in phases:
                phase_name = phase.get("name", "Unknown")
                phase_status = phase.get("status", "pending")
                emoji = status_emoji.get(phase_status, "⏳")
                
                lines.append(f"{emoji} **{phase_name}** - `{phase_status}`")
                
                if phase.get("description"):
                    lines.append(f"  *{phase.get('description')}*")
                
                lines.append("")
            
            return "\n".join(lines)
        
        return str(data)


class CheckpointListTemplate(OutputTemplate):
    """Template for checkpoint listing."""
    
    def __init__(self, format: OutputFormat = OutputFormat.TEXT):
        """Initialize checkpoint list template."""
        super().__init__("checkpoint_list", format)
    
    def render(self, data: Dict[str, Any]) -> str:
        """Render checkpoint list."""
        checkpoints = data.get("checkpoints", [])
        
        if self.format == OutputFormat.JSON:
            return json.dumps(data, indent=2)
        
        elif self.format == OutputFormat.TEXT:
            lines = ["Checkpoints", "=" * 50, ""]
            
            if not checkpoints:
                lines.append("No checkpoints available.")
                return "\n".join(lines)
            
            for cp in checkpoints:
                lines.append(f"ID: {cp.get('checkpoint_id', 'unknown')}")
                lines.append(f"Name: {cp.get('name', 'unnamed')}")
                lines.append(f"Timestamp: {cp.get('timestamp', 'unknown')}")
                lines.append(f"Status: {cp.get('status', 'unknown')}")
                lines.append(f"Size: {cp.get('size_bytes', 0)} bytes")
                
                if cp.get("tags"):
                    lines.append(f"Tags: {', '.join(cp['tags'])}")
                
                lines.append("")
            
            return "\n".join(lines)
        
        elif self.format == OutputFormat.TABLE:
            lines = []
            lines.append("| ID | Name | Timestamp | Status | Size |")
            lines.append("|----|------|-----------|--------|------|")
            
            for cp in checkpoints:
                lines.append(
                    f"| {cp.get('checkpoint_id', '-')} | "
                    f"{cp.get('name', '-')} | "
                    f"{cp.get('timestamp', '-')} | "
                    f"{cp.get('status', '-')} | "
                    f"{cp.get('size_bytes', 0)} |"
                )
            
            return "\n".join(lines)
        
        return str(data)


class PrereqCheckTemplate(OutputTemplate):
    """Template for prerequisite check results."""
    
    def __init__(self, format: OutputFormat = OutputFormat.TEXT):
        """Initialize prerequisite check template."""
        super().__init__("prereq_check", format)
    
    def render(self, data: Dict[str, Any]) -> str:
        """Render prerequisite check results."""
        summary = data.get("summary", {})
        prerequisites = data.get("prerequisites", [])
        
        if self.format == OutputFormat.JSON:
            return json.dumps(data, indent=2)
        
        elif self.format == OutputFormat.TEXT:
            lines = ["Prerequisite Check Results", "=" * 50, ""]
            
            lines.append(f"Total Checks: {summary.get('total_checks', 0)}")
            lines.append(f"Passed: {summary.get('passed', 0)}")
            lines.append(f"Failed: {summary.get('failed', 0)}")
            lines.append(f"Warnings: {summary.get('warnings', 0)}")
            lines.append(f"Skipped: {summary.get('skipped', 0)}")
            lines.append(f"Success Rate: {summary.get('success_rate', '0%')}")
            lines.append("")
            
            if summary.get("all_required_passed"):
                lines.append("✓ All required prerequisites passed")
            else:
                lines.append("✗ Some required prerequisites failed")
            
            lines.append("")
            lines.append("Detailed Results:")
            
            for prereq in prerequisites:
                status = prereq.get("status", "unknown")
                name = prereq.get("name", "unknown")
                message = prereq.get("message", "")
                
                status_marker = "✓" if status == "passed" else "✗" if status == "failed" else "⚠"
                lines.append(f"  {status_marker} {name}")
                
                if message and status != "passed":
                    lines.append(f"    {message}")
                
                lines.append("")
            
            return "\n".join(lines)
        
        elif self.format == OutputFormat.MARKDOWN:
            all_passed = summary.get("all_required_passed", False)
            status_emoji = "✅" if all_passed else "❌"
            
            lines = [
                f"# Prerequisite Check Results {status_emoji}",
                "",
                "## Summary",
                "",
                f"- **Total Checks:** {summary.get('total_checks', 0)}",
                f"- **Passed:** {summary.get('passed', 0)}",
                f"- **Failed:** {summary.get('failed', 0)}",
                f"- **Warnings:** {summary.get('warnings', 0)}",
                f"- **Skipped:** {summary.get('skipped', 0)}",
                f"- **Success Rate:** {summary.get('success_rate', '0%')}",
                "",
                "## Detailed Results",
                ""
            ]
            
            for prereq in prerequisites:
                status = prereq.get("status", "unknown")
                name = prereq.get("name", "unknown")
                message = prereq.get("message", "")
                prereq_type = prereq.get("type", "unknown")
                
                status_emoji = {
                    "passed": "✅",
                    "failed": "❌",
                    "warning": "⚠️",
                    "skipped": "⏭️"
                }.get(status, "❓")
                
                lines.append(f"{status_emoji} **{name}**")
                lines.append(f"- Type: `{prereq_type}`")
                lines.append(f"- Status: `{status}`")
                
                if message and status != "passed":
                    lines.append(f"- Message: {message}")
                
                lines.append("")
            
            return "\n".join(lines)
        
        return str(data)


class DependencyReportTemplate(OutputTemplate):
    """Template for dependency report output."""
    
    def __init__(self, format: OutputFormat = OutputFormat.TEXT):
        """Initialize dependency report template."""
        super().__init__("dependency_report", format)
    
    def render(self, data: Dict[str, Any]) -> str:
        """Render dependency report."""
        total_nodes = data.get("total_nodes", 0)
        total_dependencies = data.get("total_dependencies", 0)
        nodes = data.get("nodes", {})
        dependency_types = data.get("dependency_types", {})
        
        if self.format == OutputFormat.JSON:
            return json.dumps(data, indent=2)
        
        elif self.format == OutputFormat.TEXT:
            lines = ["Dependency Report", "=" * 50, ""]
            
            lines.append(f"Total Nodes: {total_nodes}")
            lines.append(f"Total Dependencies: {total_dependencies}")
            lines.append("")
            
            if dependency_types:
                lines.append("Dependencies by Type:")
                for dep_type, count in dependency_types.items():
                    lines.append(f"  {dep_type}: {count}")
                lines.append("")
            
            lines.append("Node Details:")
            for node_name, node_info in nodes.items():
                lines.append(f"  {node_name}:")
                
                if node_info.get("dependencies"):
                    lines.append("    Depends on:")
                    for dep_type, deps in node_info["dependencies"].items():
                        lines.append(f"      {dep_type}: {', '.join(deps)}")
                
                if node_info.get("dependents"):
                    lines.append(f"    Required by: {', '.join(node_info['dependents'])}")
                
                lines.append("")
            
            return "\n".join(lines)
        
        elif self.format == OutputFormat.MARKDOWN:
            lines = [
                "# Dependency Report",
                "",
                "## Summary",
                "",
                f"- **Total Nodes:** {total_nodes}",
                f"- **Total Dependencies:** {total_dependencies}",
                ""
            ]
            
            if dependency_types:
                lines.append("## Dependencies by Type")
                lines.append("")
                for dep_type, count in dependency_types.items():
                    lines.append(f"- **{dep_type}:** {count}")
                lines.append("")
            
            lines.append("## Node Details")
            lines.append("")
            
            for node_name, node_info in nodes.items():
                lines.append(f"### {node_name}")
                lines.append("")
                
                if node_info.get("dependencies"):
                    lines.append("**Depends on:**")
                    for dep_type, deps in node_info["dependencies"].items():
                        lines.append(f"- `{dep_type}`: {', '.join(deps)}")
                    lines.append("")
                
                if node_info.get("dependents"):
                    lines.append(f"**Required by:** {', '.join(node_info['dependents'])}")
                    lines.append("")
            
            return "\n".join(lines)
        
        return str(data)


class TemplateEngine:
    """Engine for managing and rendering output templates."""
    
    def __init__(self):
        """Initialize the template engine."""
        self.templates: Dict[str, Dict[OutputFormat, OutputTemplate]] = {}
        self._register_default_templates()
    
    def _register_default_templates(self):
        """Register default templates."""
        template_classes = {
            "workflow_result": WorkflowResultTemplate,
            "branch_status": BranchStatusTemplate,
            "phase_progress": PhaseProgressTemplate,
            "checkpoint_list": CheckpointListTemplate,
            "prereq_check": PrereqCheckTemplate,
            "dependency_report": DependencyReportTemplate
        }
        
        for template_name, template_class in template_classes.items():
            if template_name not in self.templates:
                self.templates[template_name] = {}
            
            for format in OutputFormat:
                self.templates[template_name][format] = template_class(format)
    
    def render(
        self,
        template_name: str,
        data: Dict[str, Any],
        format: OutputFormat = OutputFormat.TEXT
    ) -> str:
        """
        Render a template with data.
        
        Args:
            template_name: Name of the template
            data: Data to populate template
            format: Output format
            
        Returns:
            Formatted output string
        """
        if template_name not in self.templates:
            return json.dumps(data, indent=2)
        
        if format not in self.templates[template_name]:
            format = OutputFormat.TEXT
        
        template = self.templates[template_name][format]
        return template.render(data)
    
    def register_template(
        self,
        template_name: str,
        template: OutputTemplate,
        format: OutputFormat
    ):
        """
        Register a custom template.
        
        Args:
            template_name: Name for the template
            template: Template instance
            format: Output format
        """
        if template_name not in self.templates:
            self.templates[template_name] = {}
        
        self.templates[template_name][format] = template


def create_template_engine() -> TemplateEngine:
    """Create a template engine instance."""
    return TemplateEngine()