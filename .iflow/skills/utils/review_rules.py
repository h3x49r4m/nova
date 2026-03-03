"""Review Rules - Configurable rules for code review automation.

This module provides configurable rules for automated code review,
including severity thresholds, blocking rules, and rule sets.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .exceptions import IFlowError, ErrorCode


class RuleSeverity(Enum):
    """Severity levels for review rules."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    BLOCKER = "blocker"


class RuleCategory(Enum):
    """Categories of review rules."""
    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"
    NAMING = "naming"


@dataclass
class ReviewRule:
    """Represents a single review rule."""
    id: str
    name: str
    description: str
    category: RuleCategory
    severity: RuleSeverity
    enabled: bool = True
    blocking: bool = False
    configurable: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    message_template: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "blocking": self.blocking,
            "configurable": self.configurable,
            "parameters": self.parameters,
            "message_template": self.message_template,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReviewRule':
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            category=RuleCategory(data["category"]),
            severity=RuleSeverity(data["severity"]),
            enabled=data.get("enabled", True),
            blocking=data.get("blocking", False),
            configurable=data.get("configurable", True),
            parameters=data.get("parameters", {}),
            message_template=data.get("message_template", ""),
            created_at=data.get("created_at", datetime.now().isoformat())
        )
    
    def evaluate(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Evaluate the rule against context.
        
        Args:
            context: Context data for evaluation
            
        Returns:
            Tuple of (passed, message)
        """
        if not self.enabled:
            return True, None
        
        # Default implementation - subclasses should override
        return True, None


@dataclass
class RuleSet:
    """Represents a collection of review rules."""
    id: str
    name: str
    description: str
    rules: List[str] = field(default_factory=list)
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule set to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rules": self.rules,
            "enabled": self.enabled,
            "created_at": self.created_at
        }


class ReviewRulesManager:
    """Manages configurable review rules."""
    
    def __init__(
        self,
        repo_root: Path,
        rules_file: Optional[Path] = None
    ):
        """
        Initialize the review rules manager.
        
        Args:
            repo_root: Repository root directory
            rules_file: Path to rules configuration file
        """
        self.repo_root = repo_root
        self.rules_file = rules_file or (repo_root / ".iflow" / "skills" / "review_rules.json")
        
        self.rules: Dict[str, ReviewRule] = {}
        self.rule_sets: Dict[str, RuleSet] = {}
        self.custom_evaluators: Dict[str, Callable] = {}
        
        self._load_rules()
        self._initialize_default_rules()
    
    def _load_rules(self):
        """Load rules from configuration file."""
        if self.rules_file.exists():
            try:
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)
                
                for rule_data in data.get("rules", []):
                    rule = ReviewRule.from_dict(rule_data)
                    self.rules[rule.id] = rule
                
                for ruleset_data in data.get("rule_sets", []):
                    ruleset = RuleSet(
                        id=ruleset_data["id"],
                        name=ruleset_data["name"],
                        description=ruleset_data["description"],
                        rules=ruleset_data.get("rules", []),
                        enabled=ruleset_data.get("enabled", True)
                    )
                    self.rule_sets[ruleset.id] = ruleset
            
            except (json.JSONDecodeError, IOError):
                pass
    
    def _save_rules(self):
        """Save rules to configuration file."""
        data = {
            "rules": [rule.to_dict() for rule in self.rules.values()],
            "rule_sets": [ruleset.to_dict() for ruleset in ruleset.values()],
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            with open(self.rules_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save rules: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def _initialize_default_rules(self):
        """Initialize default review rules."""
        default_rules = [
            ReviewRule(
                id="line-length",
                name="Line Length Limit",
                description="Lines should not exceed a maximum length",
                category=RuleCategory.CODE_QUALITY,
                severity=RuleSeverity.WARNING,
                parameters={"max_length": 100},
                message_template="Line exceeds maximum length of {max_length}: {line_number}"
            ),
            ReviewRule(
                id="function-complexity",
                name="Function Complexity",
                description="Functions should not exceed a maximum cyclomatic complexity",
                category=RuleCategory.COMPLEXITY,
                severity=RuleSeverity.ERROR,
                parameters={"max_complexity": 10},
                message_template="Function complexity {complexity} exceeds maximum {max_complexity}"
            ),
            ReviewRule(
                id="no-console",
                name="No Console Statements",
                description="Avoid console.log statements in production code",
                category=RuleCategory.CODE_QUALITY,
                severity=RuleSeverity.WARNING,
                parameters={},
                message_template="Console statement found at {line}:{column}"
            ),
            ReviewRule(
                id="no-secrets",
                name="No Secrets",
                description="No secrets or sensitive data should be committed",
                category=RuleCategory.SECURITY,
                severity=RuleSeverity.CRITICAL,
                blocking=True,
                parameters={},
                message_template="Potential secret detected: {pattern}"
            ),
            ReviewRule(
                id="test-coverage",
                name="Test Coverage",
                description="Code should meet minimum test coverage requirements",
                category=RuleCategory.TESTING,
                severity=RuleSeverity.ERROR,
                parameters={"min_coverage": 80},
                message_template="Test coverage {coverage}% below minimum {min_coverage}%"
            ),
            ReviewRule(
                id="no-unused-imports",
                name="No Unused Imports",
                description="Remove unused import statements",
                category=RuleCategory.CODE_QUALITY,
                severity=RuleSeverity.WARNING,
                parameters={},
                message_template="Unused import: {import_name}"
            ),
            ReviewRule(
                id="max-file-size",
                name="Maximum File Size",
                description="Files should not exceed a maximum size",
                category=RuleCategory.MAINTAINABILITY,
                severity=RuleSeverity.ERROR,
                parameters={"max_size_kb": 500},
                message_template="File size {size_kb}KB exceeds maximum {max_size_kb}KB"
            ),
            ReviewRule(
                id="naming-convention",
                name="Naming Convention",
                description="Follow naming conventions for identifiers",
                category=RuleCategory.NAMING,
                severity=RuleSeverity.WARNING,
                parameters={"style": "snake_case"},
                message_template="Naming convention violation: {identifier}"
            ),
            ReviewRule(
                id="doc-comments",
                name="Documentation Comments",
                description="Public functions should have documentation",
                category=RuleCategory.DOCUMENTATION,
                severity=RuleSeverity.INFO,
                parameters={"require_public": True},
                message_template="Missing documentation for function: {function_name}"
            ),
            ReviewRule(
                id="no-duplicates",
                name="No Code Duplication",
                description="Avoid code duplication",
                category=RuleCategory.DUPLICATION,
                severity=RuleSeverity.WARNING,
                parameters={"min_duplicate_lines": 5},
                message_template="Code duplication detected: {lines} lines duplicated"
            ),
            ReviewRule(
                id="no-hardcoded-secrets",
                name="No Hardcoded Secrets",
                description="No hardcoded secrets or credentials",
                category=RuleCategory.SECURITY,
                severity=RuleSeverity.CRITICAL,
                blocking=True,
                parameters={},
                message_template="Hardcoded secret detected: {pattern}"
            ),
            ReviewRule(
                id="sql-injection",
                name="SQL Injection",
                description="Prevent SQL injection vulnerabilities",
                category=RuleCategory.SECURITY,
                severity=RuleSeverity.CRITICAL,
                blocking=True,
                parameters={},
                message_template="Potential SQL injection: {location}"
            ),
            ReviewRule(
                id="xss-vulnerability",
                name="XSS Vulnerability",
                description="Prevent cross-site scripting vulnerabilities",
                category=RuleCategory.SECURITY,
                severity=RuleSeverity.CRITICAL,
                blocking=True,
                parameters={},
                message_template="Potential XSS vulnerability: {location}"
            ),
            ReviewRule(
                id="deprecated-apis",
                name="No Deprecated APIs",
                description="Avoid using deprecated APIs",
                category=RuleCategory.CODE_QUALITY,
                severity=RuleSeverity.WARNING,
                parameters={},
                message_template="Deprecated API usage: {api}"
            ),
            ReviewRule(
                id="no-eval",
                name="No eval() Usage",
                description="Avoid using eval() for security reasons",
                category=RuleCategory.SECURITY,
                severity=RuleSeverity.CRITICAL,
                blocking=True,
                parameters={},
                message_template="eval() usage detected: {location}"
            ),
            ReviewRule(
                id="error-handling",
                name="Error Handling",
                description="Proper error handling should be in place",
                category=RuleCategory.CODE_QUALITY,
                severity=RuleSeverity.ERROR,
                parameters={"require_try_catch": False},
                message_template="Missing error handling: {location}"
            )
        ]
        
        # Add rules that don't exist
        for rule in default_rules:
            if rule.id not in self.rules:
                self.rules[rule.id] = rule
    
    def register_rule(self, rule: ReviewRule):
        """
        Register a new review rule.
        
        Args:
            rule: ReviewRule to register
        """
        self.rules[rule.id] = rule
        self._save_rules()
    
    def get_rule(self, rule_id: str) -> Optional[ReviewRule]:
        """
        Get a rule by ID.
        
        Args:
            rule_id: Rule ID
            
        Returns:
            ReviewRule or None
        """
        return self.rules.get(rule_id)
    
    def enable_rule(self, rule_id: str):
        """
        Enable a rule.
        
        Args:
            rule_id: Rule ID
        """
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            self._save_rules()
    
    def disable_rule(self, rule_id: str):
        """
        Disable a rule.
        
        Args:
            rule_id: Rule ID
        """
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            self._save_rules()
    
    def configure_rule(
        self,
        rule_id: str,
        parameters: Dict[str, Any]
    ):
        """
        Configure a rule's parameters.
        
        Args:
            rule_id: Rule ID
            parameters: Parameters to set
        """
        if rule_id in self.rules:
            self.rules[rule_id].parameters.update(parameters)
            self._save_rules()
    
    def create_rule_set(
        self,
        ruleset_id: str,
        name: str,
        description: str,
        rule_ids: List[str]
    ) -> RuleSet:
        """
        Create a rule set.
        
        Args:
            ruleset_id: Rule set ID
            name: Rule set name
            description: Rule set description
            rule_ids: List of rule IDs to include
            
        Returns:
            Created RuleSet object
        """
        ruleset = RuleSet(
            id=ruleset_id,
            name=name,
            description=description,
            rules=rule_ids
        )
        
        self.rule_sets[ruleset_id] = ruleset
        self._save_rules()
        
        return ruleset
    
    def get_rules(
        self,
        category: Optional[RuleCategory] = None,
        severity: Optional[RuleSeverity] = None,
        enabled_only: bool = False
    ) -> List[ReviewRule]:
        """
        Get filtered list of rules.
        
        Args:
            category: Optional category filter
            severity: Optional severity filter
            enabled_only: Whether to only return enabled rules
            
        Returns:
            List of matching rules
        """
        rules = list(self.rules.values())
        
        if category:
            rules = [r for r in rules if r.category == category]
        
        if severity:
            rules = [r for r in rules if r.severity == severity]
        
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        return rules
    
    def get_blocking_rules(self) -> List[ReviewRule]:
        """
        Get all blocking rules.
        
        Returns:
            List of blocking rules
        """
        return [r for r in self.rules.values() if r.blocking and r.enabled]
    
    def evaluate_rules(
        self,
        context: Dict[str, Any],
        ruleset_id: Optional[str] = None
    ) -> Tuple[List[Tuple[ReviewRule, bool, Optional[str]]], bool]:
        """
        Evaluate rules against context.
        
        Args:
            context: Context data for evaluation
            ruleset_id: Optional rule set ID to use
            
        Returns:
            Tuple of (results, passed_all)
        """
        # Determine which rules to evaluate
        if ruleset_id and ruleset_id in self.rule_sets:
            rule_ids = self.rule_sets[ruleset_id].rules
            rules = [self.rules[rid] for rid in rule_ids if rid in self.rules]
        else:
            rules = [r for r in self.rules.values() if r.enabled]
        
        results = []
        passed_all = True
        
        for rule in rules:
            # Check if custom evaluator exists
            if rule.id in self.custom_evaluators:
                try:
                    passed, message = self.custom_evaluators[rule.id](context)
                    results.append((rule, passed, message))
                    
                    if not passed:
                        passed_all = False
                except Exception as e:
                    results.append((rule, False, f"Rule evaluation error: {str(e)}"))
                    passed_all = False
            else:
                # Use default evaluation
                passed, message = rule.evaluate(context)
                results.append((rule, passed, message))
                
                if not passed:
                    passed_all = False
        
        return results, passed_all
    
    def register_custom_evaluator(
        self,
        rule_id: str,
        evaluator: Callable
    ):
        """
        Register a custom rule evaluator.
        
        Args:
            rule_id: Rule ID
            evaluator: Evaluator function
        """
        self.custom_evaluators[rule_id] = evaluator
    
    def export_rules(self, output_file: Optional[Path] = None) -> str:
        """
        Export rules configuration.
        
        Args:
            output_file: Optional file to save to
            
        Returns:
            JSON string of rules configuration
        """
        data = {
            "rules": [rule.to_dict() for rule in self.rules.values()],
            "rule_sets": [ruleset.to_dict() for ruleset in self.rule_sets.values()],
            "exported_at": datetime.now().isoformat()
        }
        
        json_str = json.dumps(data, indent=2)
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(json_str)
            except IOError as e:
                raise IFlowError(
                    f"Failed to export rules: {str(e)}",
                    ErrorCode.FILE_WRITE_ERROR
                )
        
        return json_str
    
    def import_rules(self, input_file: Path):
        """
        Import rules configuration.
        
        Args:
            input_file: File to import from
        """
        try:
            with open(input_file, 'r') as f:
                data = json.load(f)
            
            for rule_data in data.get("rules", []):
                rule = ReviewRule.from_dict(rule_data)
                self.rules[rule.id] = rule
            
            for ruleset_data in data.get("rule_sets", []):
                ruleset = RuleSet(
                    id=ruleset_data["id"],
                    name=ruleset_data["name"],
                    description=ruleset_data["description"],
                    rules=ruleset_data.get("rules", [])
                )
                self.rule_sets[ruleset.id] = ruleset
            
            self._save_rules()
        
        except (json.JSONDecodeError, IOError) as e:
            raise IFlowError(
                f"Failed to import rules: {str(e)}",
                ErrorCode.FILE_READ_ERROR
            )


def create_rules_manager(
    repo_root: Path,
    rules_file: Optional[Path] = None
) -> ReviewRulesManager:
    """Create a review rules manager instance."""
    return ReviewRulesManager(repo_root, rules_file)