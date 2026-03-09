#!/usr/bin/env python3
"""
Configuration Templates
Standardized configuration templates for different skill types.
"""

from typing import Dict, List, Optional, Any
from .config_manager import SkillType


class ConfigTemplates:
    """Standardized configuration templates for skills."""

    @staticmethod
    def role_config(
        name: str,
        description: str,
        capabilities: List[str],
        dependencies: Optional[List[Dict[str, str]]] = None,
        domains: Optional[Dict[str, Any]] = None,
        compatible_pipelines: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a standard role skill configuration.

        Args:
            name: Name of the role
            description: Description of the role
            capabilities: List of capabilities
            dependencies: List of dependencies (optional)
            domains: Domain support configuration (optional)
            compatible_pipelines: List of compatible pipelines (optional)

        Returns:
            Role configuration dictionary
        """
        return {
            "name": name,
            "version": "1.0.0",
            "description": description,
            "type": SkillType.ROLE.value,
            "capabilities": capabilities,
            "dependencies": dependencies or [],
            "settings": {
                "type": SkillType.ROLE.value,
                "domains": domains or {},
                "compatible_pipelines": compatible_pipelines or ["*"]
            }
        }

    @staticmethod
    def pipeline_config(
        name: str,
        description: str,
        stages: List[Dict[str, Any]],
        capabilities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a standard pipeline configuration.

        Args:
            name: Name of the pipeline
            description: Description of the pipeline
            stages: List of pipeline stages
            capabilities: List of capabilities (optional)

        Returns:
            Pipeline configuration dictionary
        """
        return {
            "name": name,
            "version": "1.0.0",
            "description": description,
            "type": SkillType.PIPELINE.value,
            "capabilities": capabilities or [],
            "stages": stages,
            "settings": {
                "type": SkillType.PIPELINE.value,
                "auto_commit": True,
                "require_approval": True
            }
        }

    @staticmethod
    def domain_config(
        enabled: bool,
        technologies: Optional[List[str]] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a domain configuration entry.

        Args:
            enabled: Whether the domain is supported
            technologies: List of technologies (optional)
            reason: Reason for support status (optional)

        Returns:
            Domain configuration dictionary
        """
        config: Dict[str, Any] = {"supported": enabled}

        if technologies:
            config["technologies"] = technologies

        if reason:
            config["reason"] = reason

        return config

    @staticmethod
    def dependency_config(
        name: str,
        min_version: Optional[str] = None,
        max_version: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create a dependency configuration entry.

        Args:
            name: Name of the dependency
            min_version: Minimum version (optional)
            max_version: Maximum version (optional)

        Returns:
            Dependency configuration dictionary
        """
        dep: Dict[str, str] = {"name": name}

        if min_version:
            dep["min_version"] = min_version

        if max_version:
            dep["max_version"] = max_version

        return dep

    @staticmethod
    def stage_config(
        name: str,
        role: str,
        order: int,
        required: bool,
        dependencies: Optional[List[int]] = None,
        skill: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a pipeline stage configuration.

        Args:
            name: Name of the stage
            role: Role responsible for the stage
            order: Order of the stage in the pipeline
            required: Whether the stage is required
            dependencies: List of stage dependencies (optional)
            skill: Skill to invoke (optional)

        Returns:
            Stage configuration dictionary
        """
        stage: Dict[str, Any] = {
            "name": name,
            "role": role,
            "order": order,
            "required": required
        }

        if dependencies:
            stage["dependencies"] = dependencies

        if skill:
            stage["skill"] = skill

        return stage


# Pre-defined domain configurations
class DomainPresets:
    """Pre-defined domain configurations for common use cases."""

    FULL_STACK = {
        "backend": ConfigTemplates.domain_config(True, ["python", "nodejs", "java", "go", "rust"]),
        "frontend": ConfigTemplates.domain_config(True, ["react", "vue", "angular", "vanilla-js"]),
        "database": ConfigTemplates.domain_config(True, ["postgresql", "mysql", "mongodb", "redis"]),
        "devops": ConfigTemplates.domain_config(True, ["docker", "kubernetes", "aws", "gcp", "azure"]),
        "testing": ConfigTemplates.domain_config(True, ["pytest", "jest", "cypress", "selenium"])
    }

    BACKEND_ONLY = {
        "backend": ConfigTemplates.domain_config(True, ["python", "nodejs", "java", "go", "rust"]),
        "database": ConfigTemplates.domain_config(True, ["postgresql", "mysql", "mongodb", "redis"]),
        "frontend": ConfigTemplates.domain_config(False, reason="Backend-focused role"),
        "devops": ConfigTemplates.domain_config(False, reason="DevOps handled by DevOps Engineer")
    }

    FRONTEND_ONLY = {
        "frontend": ConfigTemplates.domain_config(True, ["react", "vue", "angular", "vanilla-js"]),
        "backend": ConfigTemplates.domain_config(False, reason="Frontend-focused role"),
        "database": ConfigTemplates.domain_config(False, reason="Backend handled by Backend Engineer")
    }

    ARCHITECTURE = {
        "architecture": ConfigTemplates.domain_config(True),
        "technical-leadership": ConfigTemplates.domain_config(True),
        "implementation": ConfigTemplates.domain_config(True, reason="May provide code examples"),
        "deployment": ConfigTemplates.domain_config(False, reason="Deployment handled by DevOps Engineer")
    }

    PRODUCT_MANAGEMENT = {
        "business-analysis": ConfigTemplates.domain_config(True),
        "product-management": ConfigTemplates.domain_config(True),
        "technical-implementation": ConfigTemplates.domain_config(False, reason="Technical implementation handled by Software Engineer")
    }

    QA = {
        "testing": ConfigTemplates.domain_config(True, ["pytest", "jest", "cypress", "selenium", "robot"]),
        "quality-assurance": ConfigTemplates.domain_config(True),
        "automation": ConfigTemplates.domain_config(True),
        "manual-testing": ConfigTemplates.domain_config(True)
    }

    DEVOPS = {
        "devops": ConfigTemplates.domain_config(True, ["docker", "kubernetes", "aws", "gcp", "azure", "terraform"]),
        "ci-cd": ConfigTemplates.domain_config(True, ["jenkins", "gitlab-ci", "github-actions", "circleci"]),
        "infrastructure": ConfigTemplates.domain_config(True),
        "monitoring": ConfigTemplates.domain_config(True, ["prometheus", "grafana", "elk-stack", "datadog"])
    }

    SECURITY = {
        "security": ConfigTemplates.domain_config(True),
        "penetration-testing": ConfigTemplates.domain_config(True),
        "vulnerability-scanning": ConfigTemplates.domain_config(True),
        "compliance": ConfigTemplates.domain_config(True),
        "implementation": ConfigTemplates.domain_config(False, reason="Security review only, no implementation")
    }


# Pre-defined role configurations
class RolePresets:
    """Pre-defined role configurations for common roles."""

    CLIENT = ConfigTemplates.role_config(
        name="client",
        description="Requirements provider and stakeholder",
        capabilities=[
            "requirements-gathering",
            "acceptance-criteria-definition",
            "stakeholder-communication",
            "feature-extraction",
            "project-initialization"
        ],
        domains=DomainPresets.PRODUCT_MANAGEMENT,
        compatible_pipelines=["team-pipeline-new-project", "team-pipeline-new-feature"]
    )

    PRODUCT_MANAGER = ConfigTemplates.role_config(
        name="product-manager",
        description="Feature planning and prioritization",
        capabilities=[
            "feature-planning",
            "prioritization",
            "roadmap-management",
            "user-story-creation",
            "requirement-analysis"
        ],
        dependencies=[ConfigTemplates.dependency_config("client")],
        domains=DomainPresets.PRODUCT_MANAGEMENT
    )

    TECH_LEAD = ConfigTemplates.role_config(
        name="tech-lead",
        description="Architecture design and technical strategy",
        capabilities=[
            "architecture-design",
            "technical-strategy",
            "code-review",
            "technology-selection",
            "design-patterns",
            "system-design"
        ],
        dependencies=[ConfigTemplates.dependency_config("project-manager")],
        domains=DomainPresets.ARCHITECTURE
    )

    SOFTWARE_ENGINEER = ConfigTemplates.role_config(
        name="software-engineer",
        description="Full-stack software development",
        capabilities=[
            "backend",
            "frontend",
            "full-stack",
            "api-development",
            "database",
            "authentication"
        ],
        domains=DomainPresets.FULL_STACK
    )

    TESTING_ENGINEER = ConfigTemplates.role_config(
        name="testing-engineer",
        description="Test automation and frameworks",
        capabilities=[
            "test-automation",
            "unit-testing",
            "integration-testing",
            "e2e-testing",
            "test-frameworks"
        ],
        domains=DomainPresets.QA
    )

    QA_ENGINEER = ConfigTemplates.role_config(
        name="qa-engineer",
        description="Quality validation and manual testing",
        capabilities=[
            "quality-assurance",
            "manual-testing",
            "acceptance-testing",
            "bug-reporting",
            "test-planning"
        ],
        domains=DomainPresets.QA
    )

    DEVOPS_ENGINEER = ConfigTemplates.role_config(
        name="devops-engineer",
        description="CI/CD and infrastructure",
        capabilities=[
            "ci-cd",
            "infrastructure",
            "deployment",
            "monitoring",
            "containerization"
        ],
        domains=DomainPresets.DEVOPS
    )

    SECURITY_ENGINEER = ConfigTemplates.role_config(
        name="security-engineer",
        description="Security validation and scanning",
        capabilities=[
            "security-review",
            "vulnerability-scanning",
            "penetration-testing",
            "compliance-checking",
            "threat-modeling"
        ],
        domains=DomainPresets.SECURITY
    )

    DOCUMENTATION_SPECIALIST = ConfigTemplates.role_config(
        name="documentation-specialist",
        description="Documentation creation",
        capabilities=[
            "technical-writing",
            "api-documentation",
            "user-guides",
            "documentation-review",
            "knowledge-management"
        ],
        domains={
            "documentation": ConfigTemplates.domain_config(True),
            "implementation": ConfigTemplates.domain_config(False, reason="Documentation only")
        }
    )

    UI_UX_DESIGNER = ConfigTemplates.role_config(
        name="ui-ux-designer",
        description="Design creation and user experience",
        capabilities=[
            "ui-design",
            "ux-design",
            "prototyping",
            "user-research",
            "design-systems"
        ],
        domains={
            "design": ConfigTemplates.domain_config(True, ["figma", "sketch", "adobe-xd", "invision"]),
            "implementation": ConfigTemplates.domain_config(False, reason="Design only, implementation handled by Software Engineer")
        }
    )

    PROJECT_MANAGER = ConfigTemplates.role_config(
        name="project-manager",
        description="Sprint planning and resource allocation",
        capabilities=[
            "project-planning",
            "resource-allocation",
            "sprint-management",
            "timeline-tracking",
            "risk-management"
        ],
        domains={
            "project-management": ConfigTemplates.domain_config(True),
            "technical-implementation": ConfigTemplates.domain_config(False, reason="Technical work handled by Software Engineer")
        }
    )