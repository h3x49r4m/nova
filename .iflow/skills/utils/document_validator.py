"""Document Validator - Validates documents before workflow steps.

This module provides functionality for validating required documents
exist and meet quality standards before proceeding with workflow steps.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .schema_validator import SchemaValidator


class DocumentValidator:
    """Validates documents before workflow steps."""
    
    def __init__(self, repo_root: Path, schema_dir: Optional[Path] = None):
        """
        Initialize the document validator.
        
        Args:
            repo_root: Repository root directory
            schema_dir: Directory containing document schemas
        """
        self.repo_root = repo_root
        self.schema_dir = schema_dir or (repo_root / ".iflow" / "schemas")
        self.shared_state_dir = repo_root / ".iflow" / "skills" / ".shared-state"
        self.schema_validator = SchemaValidator(self.schema_dir)
        self.validation_log = repo_root / ".iflow" / "document_validation_log.json"
    
    def validate_required_documents(
        self,
        phase_name: str,
        required_docs: List[str]
    ) -> Tuple[int, str, List[Dict[str, Any]]]:
        """
        Validate that all required documents exist for a phase.
        
        Args:
            phase_name: Name of the phase
            required_docs: List of required document names
            
        Returns:
            Tuple of (exit_code, output_message, validation_results)
        """
        results = []
        all_valid = True
        
        for doc_name in required_docs:
            result = {
                "document": doc_name,
                "phase": phase_name,
                "exists": False,
                "valid": False,
                "message": "",
                "issues": []
            }
            
            # Find the document
            doc_path = self._find_document(doc_name)
            
            if not doc_path or not doc_path.exists():
                result["message"] = f"Required document not found: {doc_name}"
                result["exists"] = False
                all_valid = False
            else:
                result["exists"] = True
                
                # Validate document content
                is_valid, issues = self._validate_document_content(doc_path, doc_name)
                result["valid"] = is_valid
                result["issues"] = issues
                
                if is_valid:
                    result["message"] = f"Document validated: {doc_name}"
                else:
                    result["message"] = f"Document validation failed: {doc_name}"
                    all_valid = False
            
            results.append(result)
        
        # Log validation results
        self._log_validation(phase_name, results)
        
        if all_valid:
            return 0, f"All required documents validated for phase: {phase_name}", results
        else:
            invalid_count = sum(1 for r in results if not r["valid"])
            return 1, f"{invalid_count} document(s) failed validation for phase: {phase_name}", results
    
    def _find_document(self, doc_name: str) -> Optional[Path]:
        """Find a document by name in the repository."""
        # Search in shared state templates
        template_dir = self.shared_state_dir / "templates"
        if template_dir.exists():
            template_path = template_dir / f"{doc_name}.template.md"
            if template_path.exists():
                return template_path
            
            # Try without .template suffix
            template_path = template_dir / f"{doc_name}.md"
            if template_path.exists():
                return template_path
        
        # Search in docs directory
        docs_dir = self.repo_root / "docs"
        if docs_dir.exists():
            for path in docs_dir.rglob(f"*{doc_name}*"):
                if path.suffix in [".md", ".txt", ".rst"]:
                    return path
        
        # Search in iflow docs
        iflow_docs = self.repo_root / ".iflow" / "docs"
        if iflow_docs.exists():
            for path in iflow_docs.rglob(f"*{doc_name}*"):
                if path.suffix in [".md", ".txt", ".rst"]:
                    return path
        
        return None
    
    def _validate_document_content(
        self,
        doc_path: Path,
        doc_name: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate document content.
        
        Args:
            doc_path: Path to the document
            doc_name: Name of the document
            
        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []
        
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if document is empty
            if not content.strip():
                issues.append("Document is empty")
            
            # Check for required sections
            required_sections = self._get_required_sections(doc_name)
            
            for section in required_sections:
                if section.lower() not in content.lower():
                    issues.append(f"Missing required section: {section}")
            
            # Check document length
            if len(content) < 100:
                issues.append("Document appears too short (< 100 characters)")
            
            # Check for TODO/FIXME markers
            if "TODO" in content or "FIXME" in content or "XXX" in content:
                issues.append("Document contains TODO/FIXME markers")
            
            # Validate against schema if available
            schema_name = self._get_schema_name(doc_name)
            if schema_name:
                try:
                    is_schema_valid, schema_errors = self.schema_validator.validate(
                        {"content": content},
                        schema_name
                    )
                    if not is_schema_valid:
                        issues.extend([f"Schema error: {err}" for err in schema_errors])
                except Exception as e:
                    self.logger.warning(f"Schema validation error: {e}")
                    pass
            
            return len(issues) == 0, issues
        
        except UnicodeDecodeError:
            return False, ["Failed to read document (encoding issue)"]
        except Exception as e:
            self.logger.error(f"Document validation failed: {e}")
            return False, [f"Failed to validate document: {e}"]
    
    def _get_required_sections(self, doc_name: str) -> List[str]:
        """Get required sections for a document type."""
        section_requirements = {
            "architecture-spec": ["Introduction", "Architecture", "Components", "Dependencies"],
            "design-spec": ["Overview", "Design", "Implementation", "Testing"],
            "implementation-plan": ["Objectives", "Tasks", "Timeline", "Resources"],
            "test-plan": ["Scope", "Test Cases", "Environment", "Schedule"],
            "quality-report": ["Summary", "Metrics", "Issues", "Recommendations"],
            "security-report": ["Executive Summary", "Findings", "Recommendations", "Appendix"],
            "deployment-status": ["Environment", "Status", "Issues", "Next Steps"],
            "project-spec": ["Overview", "Requirements", "Architecture", "Timeline"],
            "api-docs": ["Overview", "Endpoints", "Examples", "Error Handling"],
            "user-guide": ["Installation", "Usage", "Examples", "Troubleshooting"],
            "changelog": ["Version", "Changes", "Date"]
        }
        
        return section_requirements.get(doc_name, [])
    
    def _get_schema_name(self, doc_name: str) -> Optional[str]:
        """Get the schema name for a document type."""
        schema_mapping = {
            "architecture-spec": "architecture-spec",
            "design-spec": "design-spec",
            "implementation-plan": "implementation-plan",
            "test-plan": "test-plan",
            "quality-report": "quality-report",
            "security-report": "security-report",
            "deployment-status": "deployment-status",
            "project-spec": "project-spec",
            "api-docs": "api-docs",
            "user-guide": "user-guide",
            "changelog": "changelog"
        }
        
        return schema_mapping.get(doc_name)
    
    def validate_document_completeness(
        self,
        doc_path: Path
    ) -> Tuple[int, str, Dict[str, Any]]:
        """
        Validate the completeness of a document.
        
        Args:
            doc_path: Path to the document
            
        Returns:
            Tuple of (exit_code, output_message, completeness_data)
        """
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            completeness_data = {
                "path": str(doc_path),
                "size_bytes": len(content.encode('utf-8')),
                "line_count": len(content.splitlines()),
                "word_count": len(content.split()),
                "char_count": len(content),
                "has_headers": self._has_headers(content),
                "has_code_blocks": "```" in content,
                "has_lists": any(line.strip().startswith(("-", "*", "+")) for line in content.splitlines()),
                "has_links": "[" in content and "]" in content and "(" in content and ")" in content,
                "completeness_score": 0,
                "assessment": ""
            }
            
            # Calculate completeness score
            score = 0
            max_score = 5
            
            if completeness_data["size_bytes"] > 500:
                score += 1
            if completeness_data["has_headers"]:
                score += 1
            if completeness_data["has_code_blocks"] or completeness_data["has_lists"]:
                score += 1
            if completeness_data["has_links"]:
                score += 1
            if completeness_data["word_count"] > 100:
                score += 1
            
            completeness_data["completeness_score"] = int((score / max_score) * 100)
            
            if completeness_data["completeness_score"] >= 80:
                completeness_data["assessment"] = "Excellent"
                exit_code = 0
            elif completeness_data["completeness_score"] >= 60:
                completeness_data["assessment"] = "Good"
                exit_code = 0
            elif completeness_data["completeness_score"] >= 40:
                completeness_data["assessment"] = "Fair"
                exit_code = 1
            else:
                completeness_data["assessment"] = "Poor"
                exit_code = 1
            
            message = f"Document completeness: {completeness_data['assessment']} ({completeness_data['completeness_score']}%)"
            
            return exit_code, message, completeness_data
        
        except Exception as e:
            return 1, f"Failed to validate document completeness: {str(e)}", {}
    
    def _has_headers(self, content: str) -> bool:
        """Check if content has markdown headers."""
        lines = content.splitlines()
        for line in lines:
            if line.startswith("#"):
                return True
        return False
    
    def generate_validation_report(
        self,
        results: List[Dict[str, Any]],
        output_file: Optional[Path] = None
    ) -> str:
        """
        Generate a document validation report.
        
        Args:
            results: Validation results
            output_file: Optional file to save the report
            
        Returns:
            Formatted report string
        """
        lines = ["Document Validation Report", "=" * 50]
        lines.append(f"Generated: {datetime.now().isoformat()}")
        
        # Group by phase
        phase_groups = {}
        for result in results:
            phase = result["phase"]
            if phase not in phase_groups:
                phase_groups[phase] = []
            phase_groups[phase].append(result)
        
        for phase, phase_results in phase_groups.items():
            lines.append(f"\nPhase: {phase}")
            lines.append("-" * 40)
            
            for result in phase_results:
                status = "✓" if result["valid"] else "✗"
                lines.append(f"{status} {result['document']}")
                lines.append(f"  Exists: {result['exists']}")
                lines.append(f"  Valid: {result['valid']}")
                lines.append(f"  Message: {result['message']}")
                
                if result["issues"]:
                    lines.append("  Issues:")
                    for issue in result["issues"]:
                        lines.append(f"    - {issue}")
        
        report = "\n".join(lines)
        
        if output_file:
            try:
                report_data = {
                    "timestamp": datetime.now().isoformat(),
                    "summary": {
                        "total_documents": len(results),
                        "valid": sum(1 for r in results if r["valid"]),
                        "invalid": sum(1 for r in results if not r["valid"])
                    },
                    "results": results,
                    "report_text": report
                }
                
                with open(output_file, 'w') as f:
                    json.dump(report_data, f, indent=2)
            
            except Exception as e:
                self.logger.warning(f"Failed to write report to {output_file}: {e}")
                pass
        
        return report
    
    def _log_validation(self, phase_name: str, results: List[Dict[str, Any]]):
        """Log validation results to file."""
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "phase": phase_name,
                "results": results
            }
            
            # Load existing log
            existing_log = []
            if self.validation_log.exists():
                with open(self.validation_log, 'r') as f:
                    existing_log = json.load(f)
            
            # Add new validation
            existing_log.append(log_data)
            
            # Keep only last 100 entries
            existing_log = existing_log[-100:]
            
            # Save log
            with open(self.validation_log, 'w') as f:
                json.dump(existing_log, f, indent=2)
        
        except Exception as e:
            self.logger.warning(f"Failed to save validation log: {e}")
            pass
    
    def get_validation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get the document validation history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of validation entries
        """
        try:
            if not self.validation_log.exists():
                return []
            
            with open(self.validation_log, 'r') as f:
                log = json.load(f)
            
            return log[-limit:]
        
        except Exception as e:
            self.logger.warning(f"Failed to load validation history: {e}")
            return []


def create_document_validator(
    repo_root: Path,
    schema_dir: Optional[Path] = None
) -> DocumentValidator:
    """Create a document validator instance."""
    return DocumentValidator(
        repo_root=repo_root,
        schema_dir=schema_dir
    )