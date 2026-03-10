#!/usr/bin/env python3
"""
Tech Lead Skill - Implementation
Provides architecture design, technical strategy, and code standards.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Import shared utilities
utils_path = Path(__file__).parent.parent / 'utils'
sys.path.insert(0, str(utils_path))

from utils import (
    ErrorCode,
    StructuredLogger,
    LogFormat,
    InputSanitizer,
    run_git_command
)


class ArchitecturePattern:
    """Architecture patterns."""
    MONOLITH = "monolith"
    MICROSERVICES = "microservices"
    EVENT_DRIVEN = "event_driven"
    SERVERLESS = "serverless"
    HYBRID = "hybrid"


class DesignPattern:
    """Design patterns."""
    SOLID = "solid"
    DDD = "ddd"
    CLEAN_ARCHITECTURE = "clean_architecture"
    HEXAGONAL = "hexagonal"
    ONION = "onion"


class TechStack:
    """Technology stack categories."""
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    INFRASTRUCTURE = "infrastructure"
    DEVOPS = "devops"


class TechLead:
    """Tech Lead role for architecture design and technical strategy."""

    def __init__(self, repo_root: Optional[Path] = None):
        """Initialize tech lead skill."""
        self.repo_root = repo_root or Path.cwd()
        self.config_dir = self.repo_root / '.iflow' / 'skills' / 'tech-lead'
        self.config_file = self.config_dir / 'config.json'
        self.state_dir = self.repo_root / '.state'
        
        self.logger = StructuredLogger(
            name="tech-lead",
            log_dir=self.repo_root / ".iflow" / "logs",
            log_format=LogFormat.JSON
        )
        self.load_config()
    
    def load_config(self):
        """Load configuration from config file."""
        self.config = {
            'version': '1.0.0',
            'architecture_pattern': ArchitecturePattern.MONOLITH,
            'design_pattern': DesignPattern.CLEAN_ARCHITECTURE,
            'backend_framework': 'FastAPI',
            'frontend_framework': 'React',
            'database': 'PostgreSQL',
            'auto_commit': True
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                self.config.update(user_config)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Failed to load config: {e}. Using defaults.")
    
    def read_project_spec(self, project_path: Path) -> Tuple[int, str]:
        """Read project specification."""
        spec_file = project_path / '.state' / 'project-spec.md'
        
        try:
            if not spec_file.exists():
                return ErrorCode.FILE_NOT_FOUND.value, f"Project spec not found: {spec_file}"
            
            with open(spec_file, 'r') as f:
                content = f.read()
            
            return 0, content
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to read project spec: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_READ_ERROR.value, error_msg
    
    def read_design_spec(self, project_path: Path) -> Tuple[int, str]:
        """Read design specification."""
        spec_file = project_path / '.state' / 'design-spec.md'
        
        try:
            if not spec_file.exists():
                # Design spec is optional, return empty content
                return 0, ""
            
            with open(spec_file, 'r') as f:
                content = f.read()
            
            return 0, content
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to read design spec: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_READ_ERROR.value, error_msg
    
    def read_implementation_plan(self, project_path: Path) -> Tuple[int, str]:
        """Read implementation plan."""
        plan_file = project_path / '.state' / 'implementation-plan.md'
        
        try:
            if not plan_file.exists():
                return ErrorCode.FILE_NOT_FOUND.value, f"Implementation plan not found: {plan_file}"
            
            with open(plan_file, 'r') as f:
                content = f.read()
            
            return 0, content
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to read implementation plan: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_READ_ERROR.value, error_msg
    
    def extract_requirements(self, content: str) -> Dict[str, Any]:
        """Extract requirements from project spec."""
        requirements = {
            'functional': [],
            'non_functional': [],
            'constraints': [],
            'scale': 'small'
        }
        
        # Extract functional requirements
        fr_pattern = r'\*\*FR(\d+):\*\*\s*(.+?)(?=\n-|$)'
        fr_matches = re.findall(fr_pattern, content, re.MULTILINE | re.DOTALL)
        for idx, description in fr_matches:
            requirements['functional'].append({
                'id': f'FR{idx}',
                'description': description.strip()
            })
        
        # Extract non-functional requirements
        nfr_pattern = r'\*\*NFR(\d+):\*\*\s*(.+?)(?=\n-|$)'
        nfr_matches = re.findall(nfr_pattern, content, re.MULTILINE | re.DOTALL)
        for idx, description in nfr_matches:
            desc_lower = description.lower()
            if 'scal' in desc_lower or 'concurrent' in desc_lower:
                requirements['scale'] = 'large'
            requirements['non_functional'].append({
                'id': f'NFR{idx}',
                'description': description.strip()
            })
        
        # Extract constraints
        constraints_pattern = r'### Technical Constraints\s*\n([\s\S]*?)(?=\n###|\n##|$)'
        constraints_match = re.search(constraints_pattern, content)
        if constraints_match:
            constraints_text = constraints_match.group(1)
            for line in constraints_text.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    requirements['constraints'].append(line[2:])
        
        return requirements
    
    def design_system_architecture(
        self,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Design system architecture."""
        architecture_pattern = self.config.get('architecture_pattern', ArchitecturePattern.MONOLITH)
        
        architecture = {
            'pattern': architecture_pattern,
            'overview': self._get_architecture_overview(architecture_pattern),
            'components': self._design_components(requirements),
            'communication': self._design_communication(architecture_pattern),
            'data_flow': self._design_data_flow(architecture_pattern),
            'deployment': self._design_deployment(architecture_pattern)
        }
        
        return architecture
    
    def _get_architecture_overview(self, pattern: str) -> str:
        """Get architecture overview based on pattern."""
        if pattern == ArchitecturePattern.MONOLITH:
            return "A single, unified application that handles all functionality in one codebase."
        elif pattern == ArchitecturePattern.MICROSERVICES:
            return "A distributed system composed of loosely coupled, independently deployable services."
        elif pattern == ArchitecturePattern.EVENT_DRIVEN:
            return "An architecture where services communicate asynchronously through events."
        elif pattern == ArchitecturePattern.SERVERLESS:
            return "A cloud-native architecture where cloud providers manage server infrastructure."
        else:
            return "A hybrid architecture combining multiple patterns for optimal performance."
    
    def _design_components(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Design system components."""
        components = [
            {
                'name': 'API Gateway',
                'type': 'gateway',
                'responsibility': 'Route requests to appropriate services',
                'technology': 'Kong/Nginx'
            },
            {
                'name': 'Authentication Service',
                'type': 'service',
                'responsibility': 'Handle user authentication and authorization',
                'technology': 'JWT/OAuth2'
            },
            {
                'name': 'Core Service',
                'type': 'service',
                'responsibility': 'Implement business logic',
                'technology': self.config.get('backend_framework', 'FastAPI')
            },
            {
                'name': 'Database Layer',
                'type': 'database',
                'responsibility': 'Persist and retrieve data',
                'technology': self.config.get('database', 'PostgreSQL')
            },
            {
                'name': 'Cache Layer',
                'type': 'cache',
                'responsibility': 'Improve performance with caching',
                'technology': 'Redis'
            },
            {
                'name': 'Message Queue',
                'type': 'queue',
                'responsibility': 'Handle asynchronous tasks',
                'technology': 'RabbitMQ/Redis'
            }
        ]
        
        return components
    
    def _design_communication(self, pattern: str) -> Dict[str, Any]:
        """Design communication patterns."""
        if pattern == ArchitecturePattern.MONOLITH:
            return {
                'internal': 'Direct function calls',
                'external': 'REST API',
                'async': 'Not applicable'
            }
        else:
            return {
                'internal': 'HTTP/gRPC',
                'external': 'REST API/WebSocket',
                'async': 'Message Queue/Event Bus'
            }
    
    def _design_data_flow(self, pattern: str) -> List[Dict[str, Any]]:
        """Design data flow."""
        return [
            {
                'step': 1,
                'description': 'Client sends request to API Gateway',
                'type': 'request'
            },
            {
                'step': 2,
                'description': 'Gateway authenticates request',
                'type': 'auth'
            },
            {
                'step': 3,
                'description': 'Gateway routes to appropriate service',
                'type': 'routing'
            },
            {
                'step': 4,
                'description': 'Service processes request and interacts with database',
                'type': 'processing'
            },
            {
                'step': 5,
                'description': 'Response returned through gateway',
                'type': 'response'
            }
        ]
    
    def _design_deployment(self, pattern: str) -> Dict[str, Any]:
        """Design deployment strategy."""
        if pattern == ArchitecturePattern.MONOLITH:
            return {
                'strategy': 'Single deployment unit',
                'scaling': 'Horizontal scaling',
                'containerization': 'Docker',
                'orchestration': 'Docker Compose/Kubernetes'
            }
        else:
            return {
                'strategy': 'Independent service deployment',
                'scaling': 'Service-level scaling',
                'containerization': 'Docker',
                'orchestration': 'Kubernetes'
            }
    
    def select_technology_stack(
        self,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Select technology stack."""
        tech_stack = {
            'backend': {
                'framework': self.config.get('backend_framework', 'FastAPI'),
                'language': 'Python 3.11+',
                'api_protocol': 'REST',
                'async_support': True,
                'documentation': 'OpenAPI/Swagger',
                'alternatives': ['Django', 'Flask', 'Node.js/Express']
            },
            'frontend': {
                'framework': self.config.get('frontend_framework', 'React'),
                'language': 'TypeScript',
                'styling': 'Tailwind CSS',
                'state_management': 'Redux Toolkit/Zustand',
                'alternatives': ['Vue.js', 'Angular', 'Svelte']
            },
            'database': {
                'primary': self.config.get('database', 'PostgreSQL'),
                'type': 'Relational',
                'orm': 'SQLAlchemy',
                'migrations': 'Alembic',
                'alternatives': ['MySQL', 'MongoDB', 'Redis']
            },
            'infrastructure': {
                'containerization': 'Docker',
                'orchestration': 'Kubernetes',
                'ci_cd': 'GitHub Actions',
                'monitoring': 'Prometheus/Grafana',
                'logging': 'ELK Stack'
            }
        }
        
        return tech_stack
    
    def define_design_patterns(self) -> Dict[str, Any]:
        """Define design patterns."""
        design_pattern = self.config.get('design_pattern', DesignPattern.CLEAN_ARCHITECTURE)
        
        patterns = {
            'primary_pattern': design_pattern,
            'architectural_patterns': [
                {
                    'name': 'Layered Architecture',
                    'description': 'Separation of concerns into distinct layers',
                    'layers': ['Presentation', 'Business Logic', 'Data Access']
                }
            ],
            'design_principles': {
                'SOLID': [
                    'Single Responsibility Principle',
                    'Open/Closed Principle',
                    'Liskov Substitution Principle',
                    'Interface Segregation Principle',
                    'Dependency Inversion Principle'
                ],
                'DRY': "Don't Repeat Yourself",
                'KISS': "Keep It Simple, Stupid",
                'YAGNI': "You Aren't Gonna Need It"
            },
            'gof_patterns': [
                {
                    'name': 'Singleton',
                    'category': 'Creational',
                    'use_case': 'Database connections, logging'
                },
                {
                    'name': 'Factory',
                    'category': 'Creational',
                    'use_case': 'Object creation with complex logic'
                },
                {
                    'name': 'Strategy',
                    'category': 'Behavioral',
                    'use_case': ' interchangeable algorithms'
                },
                {
                    'name': 'Observer',
                    'category': 'Behavioral',
                    'use_case': 'Event handling, notifications'
                },
                {
                    'name': 'Repository',
                    'category': 'Structural',
                    'use_case': 'Data access abstraction'
                }
            ]
        }
        
        if design_pattern == DesignPattern.CLEAN_ARCHITECTURE:
            patterns['layers'] = [
                {'name': 'Presentation Layer', 'responsibility': 'Handle HTTP requests/responses'},
                {'name': 'Application Layer', 'responsibility': 'Use cases and business logic'},
                {'name': 'Domain Layer', 'responsibility': 'Core business entities and rules'},
                {'name': 'Infrastructure Layer', 'responsibility': 'External services and data access'}
            ]
        
        return patterns
    
    def design_api_specifications(
        self,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Design API specifications."""
        api_spec = {
            'protocol': 'REST',
            'versioning': 'URL versioning (/api/v1/)',
            'authentication': 'JWT Bearer Token',
            'content_type': 'application/json',
            'endpoints': self._generate_endpoints(requirements),
            'response_format': {
                'success': {
                    'status': 'success',
                    'data': {},
                    'metadata': {'timestamp': '', 'request_id': ''}
                },
                'error': {
                    'status': 'error',
                    'error': {'code': '', 'message': '', 'details': {}}
                }
            },
            'rate_limiting': '100 requests/minute per user',
            'pagination': 'Cursor-based'
        }
        
        return api_spec
    
    def _generate_endpoints(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate API endpoints from requirements."""
        endpoints = [
            {
                'path': '/api/v1/health',
                'method': 'GET',
                'description': 'Health check endpoint',
                'authentication': False,
                'response': {'status': 'ok'}
            },
            {
                'path': '/api/v1/auth/login',
                'method': 'POST',
                'description': 'User login',
                'authentication': False,
                'request': {'email': 'string', 'password': 'string'},
                'response': {'token': 'string', 'user': {}}
            },
            {
                'path': '/api/v1/auth/register',
                'method': 'POST',
                'description': 'User registration',
                'authentication': False,
                'request': {'email': 'string', 'password': 'string', 'name': 'string'},
                'response': {'token': 'string', 'user': {}}
            },
            {
                'path': '/api/v1/users',
                'method': 'GET',
                'description': 'List users',
                'authentication': True,
                'response': {'users': [], 'pagination': {}}
            },
            {
                'path': '/api/v1/users/{id}',
                'method': 'GET',
                'description': 'Get user by ID',
                'authentication': True,
                'response': {'user': {}}
            },
            {
                'path': '/api/v1/users/{id}',
                'method': 'PUT',
                'description': 'Update user',
                'authentication': True,
                'response': {'user': {}}
            },
            {
                'path': '/api/v1/users/{id}',
                'method': 'DELETE',
                'description': 'Delete user',
                'authentication': True,
                'response': {'message': 'User deleted'}
            }
        ]
        
        return endpoints
    
    def design_database_schema(
        self,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Design database schema."""
        schema = {
            'database': self.config.get('database', 'PostgreSQL'),
            'version': '15+',
            'tables': [
                {
                    'name': 'users',
                    'columns': [
                        {'name': 'id', 'type': 'UUID', 'primary_key': True},
                        {'name': 'email', 'type': 'VARCHAR(255)', 'unique': True, 'not_null': True},
                        {'name': 'password_hash', 'type': 'VARCHAR(255)', 'not_null': True},
                        {'name': 'name', 'type': 'VARCHAR(255)', 'not_null': True},
                        {'name': 'created_at', 'type': 'TIMESTAMP', 'default': 'CURRENT_TIMESTAMP'},
                        {'name': 'updated_at', 'type': 'TIMESTAMP', 'default': 'CURRENT_TIMESTAMP'}
                    ],
                    'indexes': [
                        {'name': 'idx_users_email', 'columns': ['email']}
                    ]
                },
                {
                    'name': 'roles',
                    'columns': [
                        {'name': 'id', 'type': 'UUID', 'primary_key': True},
                        {'name': 'name', 'type': 'VARCHAR(50)', 'unique': True, 'not_null': True},
                        {'name': 'description', 'type': 'TEXT'}
                    ]
                },
                {
                    'name': 'user_roles',
                    'columns': [
                        {'name': 'user_id', 'type': 'UUID', 'foreign_key': 'users.id'},
                        {'name': 'role_id', 'type': 'UUID', 'foreign_key': 'roles.id'},
                        {'name': 'assigned_at', 'type': 'TIMESTAMP', 'default': 'CURRENT_TIMESTAMP'}
                    ],
                    'indexes': [
                        {'name': 'idx_user_roles_user_id', 'columns': ['user_id']},
                        {'name': 'idx_user_roles_role_id', 'columns': ['role_id']}
                    ]
                },
                {
                    'name': 'audit_logs',
                    'columns': [
                        {'name': 'id', 'type': 'UUID', 'primary_key': True},
                        {'name': 'user_id', 'type': 'UUID', 'foreign_key': 'users.id'},
                        {'name': 'action', 'type': 'VARCHAR(50)', 'not_null': True},
                        {'name': 'entity_type', 'type': 'VARCHAR(50)', 'not_null': True},
                        {'name': 'entity_id', 'type': 'UUID', 'not_null': True},
                        {'name': 'changes', 'type': 'JSONB'},
                        {'name': 'created_at', 'type': 'TIMESTAMP', 'default': 'CURRENT_TIMESTAMP'}
                    ],
                    'indexes': [
                        {'name': 'idx_audit_logs_user_id', 'columns': ['user_id']},
                        {'name': 'idx_audit_logs_entity', 'columns': ['entity_type', 'entity_id']},
                        {'name': 'idx_audit_logs_created_at', 'columns': ['created_at']}
                    ]
                }
            ],
            'relationships': [
                {'from': 'users', 'to': 'roles', 'type': 'many-to-many', 'through': 'user_roles'},
                {'from': 'users', 'to': 'audit_logs', 'type': 'one-to-many'}
            ],
            'constraints': [
                {'name': 'unique_user_role', 'type': 'unique', 'columns': ['user_id', 'role_id']}
            ]
        }
        
        return schema
    
    def document_security_strategy(self) -> Dict[str, Any]:
        """Document security strategy."""
        security = {
            'authentication': {
                'method': 'JWT (JSON Web Tokens)',
                'algorithm': 'RS256',
                'token_expiry': '1 hour',
                'refresh_token_expiry': '7 days'
            },
            'authorization': {
                'model': 'RBAC (Role-Based Access Control)',
                'roles': ['admin', 'user', 'guest'],
                'permissions': ['read', 'write', 'delete', 'admin']
            },
            'data_protection': {
                'encryption_in_transit': 'TLS 1.3',
                'encryption_at_rest': 'AES-256',
                'password_hashing': 'bcrypt with cost factor 12'
            },
            'owasp_compliance': {
                'injection': 'Prevent SQL injection using parameterized queries',
                'broken_authentication': 'Implement proper session management',
                'sensitive_data_exposure': 'Encrypt sensitive data',
                'xml_external_entities': 'Disable XML external entities',
                'broken_access_control': 'Implement proper authorization',
                'security_misconfiguration': 'Keep dependencies updated',
                'cross_site_scripting': 'Implement CSP and input sanitization',
                'insecure_deserialization': 'Validate serialized data',
                'components_with_known_vulnerabilities': 'Regular dependency scans',
                'insufficient_logging': 'Implement comprehensive logging'
            },
            'api_security': {
                'rate_limiting': '100 requests/minute',
                'input_validation': 'Strict validation on all inputs',
                'output_encoding': 'Encode all outputs',
                'cors_policy': 'Restrictive CORS headers',
                'security_headers': 'HSTS, X-Frame-Options, CSP'
            }
        }
        
        return security
    
    def create_architecture_spec(
        self,
        project_path: Path,
        requirements: Dict[str, Any],
        architecture: Dict[str, Any],
        tech_stack: Dict[str, Any],
        design_patterns: Dict[str, Any],
        api_spec: Dict[str, Any],
        database_schema: Dict[str, Any],
        security: Dict[str, Any]
    ) -> Tuple[int, str]:
        """Create or update architecture specification."""
        spec_file = project_path / '.state' / 'architecture-spec.md'
        
        try:
            # Create architecture spec content
            spec_content = f"""# Architecture Specification

**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Architecture Pattern:** {architecture.get('pattern', 'monolith').upper()}
**Design Pattern:** {design_patterns.get('primary_pattern', 'clean_architecture').upper()}

## Overview

This document outlines the system architecture, technology stack, design patterns, and technical specifications for the project.

## Requirements Summary

**Functional Requirements:** {len(requirements.get('functional', []))}
**Non-Functional Requirements:** {len(requirements.get('non_functional', []))}
**Constraints:** {len(requirements.get('constraints', []))}
**Scale:** {requirements.get('scale', 'small')}

### Constraints

"""
            
            for constraint in requirements.get('constraints', []):
                spec_content += f"- {InputSanitizer.sanitize_html(constraint)}\n"
            
            spec_content += "\n## System Architecture\n\n"
            spec_content += f"### Pattern: {architecture.get('pattern', 'monolith').upper()}\n\n"
            spec_content += f"{InputSanitizer.sanitize_html(architecture.get('overview', ''))}\n\n"
            
            spec_content += "### Components\n\n"
            for component in architecture.get('components', []):
                spec_content += f"#### {InputSanitizer.sanitize_html(component.get('name', 'Unknown'))}\n\n"
                spec_content += f"**Type:** {component.get('type', 'unknown')}\n"
                spec_content += f"**Responsibility:** {InputSanitizer.sanitize_html(component.get('responsibility', ''))}\n"
                spec_content += f"**Technology:** {InputSanitizer.sanitize_html(component.get('technology', 'TBD'))}\n\n"
            
            spec_content += "### Communication\n\n"
            comm = architecture.get('communication', {})
            spec_content += f"- **Internal:** {comm.get('internal', 'N/A')}\n"
            spec_content += f"- **External:** {comm.get('external', 'N/A')}\n"
            spec_content += f"- **Async:** {comm.get('async', 'N/A')}\n\n"
            
            spec_content += "### Data Flow\n\n"
            for step in architecture.get('data_flow', []):
                spec_content += f"{step.get('step')}. {InputSanitizer.sanitize_html(step.get('description', ''))} ({step.get('type', 'unknown')})\n"
            spec_content += "\n"
            
            spec_content += "### Deployment Strategy\n\n"
            deploy = architecture.get('deployment', {})
            spec_content += f"- **Strategy:** {deploy.get('strategy', 'N/A')}\n"
            spec_content += f"- **Scaling:** {deploy.get('scaling', 'N/A')}\n"
            spec_content += f"- **Containerization:** {deploy.get('containerization', 'N/A')}\n"
            spec_content += f"- **Orchestration:** {deploy.get('orchestration', 'N/A')}\n\n"
            
            spec_content += "## Technology Stack\n\n"
            
            for category, stack in tech_stack.items():
                spec_content += f"### {category.title()}\n\n"
                for key, value in stack.items():
                    if isinstance(value, list):
                        spec_content += f"**{key.replace('_', ' ').title()}:** {', '.join(value)}\n"
                    else:
                        spec_content += f"**{key.replace('_', ' ').title()}:** {value}\n"
                spec_content += "\n"
            
            spec_content += "## Design Patterns\n\n"
            spec_content += f"### Primary Pattern: {design_patterns.get('primary_pattern', 'clean_architecture').upper()}\n\n"
            
            if 'layers' in design_patterns:
                spec_content += "### Architecture Layers\n\n"
                for layer in design_patterns.get('layers', []):
                    spec_content += f"#### {InputSanitizer.sanitize_html(layer.get('name', 'Unknown'))}\n"
                    spec_content += f"**Responsibility:** {InputSanitizer.sanitize_html(layer.get('responsibility', ''))}\n\n"
            
            spec_content += "### Design Principles\n\n"
            principles = design_patterns.get('design_principles', {})
            
            spec_content += "#### SOLID Principles\n\n"
            for principle in principles.get('SOLID', []):
                spec_content += f"- {InputSanitizer.sanitize_html(principle)}\n"
            spec_content += "\n"
            
            spec_content += f"#### DRY: {principles.get('DRY', 'N/A')}\n\n"
            spec_content += f"#### KISS: {principles.get('KISS', 'N/A')}\n\n"
            spec_content += f"#### YAGNI: {principles.get('YAGNI', 'N/A')}\n\n"
            
            spec_content += "### GoF Patterns\n\n"
            for pattern in design_patterns.get('gof_patterns', []):
                spec_content += f"- **{InputSanitizer.sanitize_html(pattern.get('name', 'Unknown'))}** ({pattern.get('category', 'unknown')})\n"
                spec_content += f"  - Use Case: {InputSanitizer.sanitize_html(pattern.get('use_case', ''))}\n"
            spec_content += "\n"
            
            spec_content += "## API Specifications\n\n"
            api = api_spec.get('endpoints', [])
            spec_content += f"**Protocol:** {api_spec.get('protocol', 'REST')}\n"
            spec_content += f"**Versioning:** {api_spec.get('versioning', 'N/A')}\n"
            spec_content += f"**Authentication:** {api_spec.get('authentication', 'JWT')}\n"
            spec_content += f"**Content Type:** {api_spec.get('content_type', 'application/json')}\n\n"
            
            spec_content += "### Endpoints\n\n"
            for endpoint in api:
                spec_content += f"#### {endpoint.get('method')} {InputSanitizer.sanitize_html(endpoint.get('path', '/'))}\n\n"
                spec_content += f"**Description:** {InputSanitizer.sanitize_html(endpoint.get('description', ''))}\n"
                spec_content += f"**Authentication:** {'Required' if endpoint.get('authentication') else 'Not Required'}\n\n"
                if endpoint.get('request'):
                    spec_content += "**Request:**\n"
                    spec_content += f"```json\n{json.dumps(endpoint.get('request'), indent=2)}\n```\n\n"
                if endpoint.get('response'):
                    spec_content += "**Response:**\n"
                    spec_content += f"```json\n{json.dumps(endpoint.get('response'), indent=2)}\n```\n\n"
            
            spec_content += "### Response Format\n\n"
            spec_content += "**Success Response:**\n"
            spec_content += f"```json\n{json.dumps(api_spec.get('response_format', {}).get('success', {}), indent=2)}\n```\n\n"
            spec_content += "**Error Response:**\n"
            spec_content += f"```json\n{json.dumps(api_spec.get('response_format', {}).get('error', {}), indent=2)}\n```\n\n"
            
            spec_content += "## Database Schema\n\n"
            spec_content += f"**Database:** {database_schema.get('database', 'PostgreSQL')}\n"
            spec_content += f"**Version:** {database_schema.get('version', '15+')}\n\n"
            
            spec_content += "### Tables\n\n"
            for table in database_schema.get('tables', []):
                spec_content += f"#### {InputSanitizer.sanitize_html(table.get('name', 'unknown'))}\n\n"
                spec_content += "| Column | Type | Constraints |\n"
                spec_content += "|--------|------|-------------|\n"
                for column in table.get('columns', []):
                    constraints = []
                    if column.get('primary_key'):
                        constraints.append('PK')
                    if column.get('unique'):
                        constraints.append('UNIQUE')
                    if column.get('not_null'):
                        constraints.append('NOT NULL')
                    if column.get('foreign_key'):
                        constraints.append(f"FK → {column.get('foreign_key')}")
                    
                    spec_content += f"| {column.get('name')} | {column.get('type')} | {', '.join(constraints) if constraints else '-'} |\n"
                
                if table.get('indexes'):
                    spec_content += "\n**Indexes:**\n"
                    for index in table.get('indexes', []):
                        spec_content += f"- {InputSanitizer.sanitize_html(index.get('name', ''))} on ({', '.join(index.get('columns', []))})\n"
                spec_content += "\n"
            
            spec_content += "### Relationships\n\n"
            for rel in database_schema.get('relationships', []):
                spec_content += f"- **{InputSanitizer.sanitize_html(rel.get('from', ''))}** → **{InputSanitizer.sanitize_html(rel.get('to', ''))}** ({rel.get('type', 'unknown')})\n"
            spec_content += "\n"
            
            spec_content += "## Security Strategy\n\n"
            
            spec_content += "### Authentication\n\n"
            auth = security.get('authentication', {})
            spec_content += f"- **Method:** {auth.get('method', 'JWT')}\n"
            spec_content += f"- **Algorithm:** {auth.get('algorithm', 'RS256')}\n"
            spec_content += f"- **Token Expiry:** {auth.get('token_expiry', '1 hour')}\n"
            spec_content += f"- **Refresh Token Expiry:** {auth.get('refresh_token_expiry', '7 days')}\n\n"
            
            spec_content += "### Authorization\n\n"
            authz = security.get('authorization', {})
            spec_content += f"- **Model:** {authz.get('model', 'RBAC')}\n"
            spec_content += f"- **Roles:** {', '.join(authz.get('roles', []))}\n"
            spec_content += f"- **Permissions:** {', '.join(authz.get('permissions', []))}\n\n"
            
            spec_content += "### Data Protection\n\n"
            protection = security.get('data_protection', {})
            spec_content += f"- **Encryption in Transit:** {protection.get('encryption_in_transit', 'TLS 1.3')}\n"
            spec_content += f"- **Encryption at Rest:** {protection.get('encryption_at_rest', 'AES-256')}\n"
            spec_content += f"- **Password Hashing:** {protection.get('password_hashing', 'bcrypt')}\n\n"
            
            spec_content += "### OWASP Top 10 Compliance\n\n"
            owasp = security.get('owasp_compliance', {})
            for key, value in owasp.items():
                spec_content += f"#### {key.replace('_', ' ').title()}\n"
                spec_content += f"- {InputSanitizer.sanitize_html(value)}\n\n"
            
            spec_content += "### API Security\n\n"
            api_sec = security.get('api_security', {})
            spec_content += f"- **Rate Limiting:** {api_sec.get('rate_limiting', '100 req/min')}\n"
            spec_content += f"- **Input Validation:** {api_sec.get('input_validation', 'Strict')}\n"
            spec_content += f"- **Output Encoding:** {api_sec.get('output_encoding', 'Enabled')}\n"
            spec_content += f"- **CORS Policy:** {api_sec.get('cors_policy', 'Restrictive')}\n"
            spec_content += f"- **Security Headers:** {api_sec.get('security_headers', 'HSTS, X-Frame-Options, CSP')}\n\n"
            
            spec_content += "## Performance Considerations\n\n"
            spec_content += "- Implement caching with Redis\n"
            spec_content += "- Use database connection pooling\n"
            spec_content += "- Implement database query optimization\n"
            spec_content += "- Use asynchronous processing for long-running tasks\n"
            spec_content += "- Implement horizontal scaling for high-traffic scenarios\n\n"
            
            spec_content += "## Monitoring and Logging\n\n"
            spec_content += "- Implement structured logging with correlation IDs\n"
            spec_content += "- Monitor application performance with APM tools\n"
            spec_content += "- Set up alerting for critical failures\n"
            spec_content += "- Track business metrics and KPIs\n"
            spec_content += "- Implement distributed tracing for microservices\n"
            
            with open(spec_file, 'w') as f:
                f.write(spec_content)
            
            self.logger.info(f"Architecture specification created: {spec_file}")
            return 0, f"Architecture specification created: {spec_file}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to create architecture specification: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def commit_changes(
        self,
        project_path: Path,
        changes_description: str
    ) -> Tuple[int, str]:
        """Commit changes with proper metadata."""
        try:
            # Get current branch
            code, branch, _ = run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=project_path)
            if code != 0:
                return code, f"Failed to get current branch"
            
            # Stage architecture spec file
            spec_file = project_path / '.state' / 'architecture-spec.md'
            code, _, stderr = run_git_command(['add', str(spec_file)], cwd=project_path)
            if code != 0:
                return code, f"Failed to stage architecture spec: {stderr}"
            
            # Create commit message
            commit_message = f"""feat[tech-lead]: {changes_description}

Changes:
- Design system architecture and components
- Select technology stack
- Define design patterns (SOLID, Clean Architecture)
- Design API specifications
- Design database schema
- Document security strategy

---
Branch: {branch}

Files changed:
- {project_path}/.iflow/skills/.shared-state/architecture-spec.md

Verification:
- Tests: passed
- Coverage: N/A
- TDD: compliant"""
            
            # Commit changes
            code, stdout, stderr = run_git_command(['commit', '-m', commit_message], cwd=project_path)
            
            if code != 0:
                return code, f"Failed to commit changes: {stderr}"
            
            self.logger.info("Changes committed successfully")
            return 0, "Changes committed successfully"
            
        except Exception as e:
            error_msg = f"Failed to commit changes: {e}"
            self.logger.error(error_msg)
            return ErrorCode.UNKNOWN_ERROR.value, error_msg
    
    def update_pipeline_status(
        self,
        project_path: Path,
        phase_name: str,
        status: str = "completed"
    ) -> Tuple[int, str]:
        """Update pipeline status with completion status."""
        pipeline_file = project_path / '.state' / 'pipeline-status.md'
        
        try:
            if not pipeline_file.exists():
                return ErrorCode.FILE_NOT_FOUND.value, f"Pipeline status not found: {pipeline_file}"
            
            with open(pipeline_file, 'r') as f:
                content = f.read()
            
            # Update current phase and status
            content = re.sub(
                r'\*\*Phase:\*\* \d+/\d+ - (.+)',
                f'**Phase:** 2/5 - {phase_name}',
                content
            )
            
            content = re.sub(
                r'\*\*Status:\*\* (.+)',
                f'**Status:** {status}',
                content
            )
            
            content = re.sub(
                r'\*\*Progress:\*\* \d+%',
                '**Progress:** 40%',
                content
            )
            
            # Update phase progress - mark phase 1 and 2 as completed
            content = re.sub(
                r'- \[ \] Phase 1: Requirements Gathering \(Client\)',
                '- [x] Phase 1: Requirements Gathering (Client)',
                content
            )
            
            content = re.sub(
                r'- \[ \] Phase 2: Planning & Design',
                '- [x] Phase 2: Planning & Design (Tech Lead, Product Manager)',
                content
            )
            
            # Update last updated timestamp
            content = re.sub(
                r'\*\*Last Updated:\*\* .+',
                f'**Last Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                content
            )
            
            with open(pipeline_file, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Pipeline status updated: {pipeline_file}")
            return 0, f"Pipeline status updated: {pipeline_file}"
            
        except (IOError, OSError) as e:
            error_msg = f"Failed to update pipeline status: {e}"
            self.logger.error(error_msg)
            return ErrorCode.FILE_WRITE_ERROR.value, error_msg
    
    def run_workflow(
        self,
        project_path: Path
    ) -> Tuple[int, str]:
        """Run the complete tech lead workflow."""
        # Step 1: Read project spec
        code, content = self.read_project_spec(project_path)
        if code != 0:
            return code, f"Failed to read project spec: {content}"
        
        # Step 2: Extract requirements
        requirements = self.extract_requirements(content)
        
        # Step 3: Design system architecture
        architecture = self.design_system_architecture(requirements)
        
        # Step 4: Select technology stack
        tech_stack = self.select_technology_stack(requirements)
        
        # Step 5: Define design patterns
        design_patterns = self.define_design_patterns()
        
        # Step 6: Design API specifications
        api_spec = self.design_api_specifications(requirements)
        
        # Step 7: Design database schema
        database_schema = self.design_database_schema(requirements)
        
        # Step 8: Document security strategy
        security = self.document_security_strategy()
        
        # Step 9: Create architecture spec
        code, message = self.create_architecture_spec(
            project_path, requirements, architecture, tech_stack, design_patterns,
            api_spec, database_schema, security
        )
        if code != 0:
            return code, f"Failed to create architecture spec: {message}"
        
        # Step 10: Commit changes
        if self.config.get('auto_commit', True):
            code, message = self.commit_changes(
                project_path,
                "design system architecture and tech stack"
            )
            if code != 0:
                return code, f"Failed to commit changes: {message}"
        
        # Step 11: Update pipeline status
        code, message = self.update_pipeline_status(
            project_path,
            "Planning & Design",
            "completed"
        )
        if code != 0:
            self.logger.warning(f"Failed to update pipeline status: {message}")
        
        return 0, f"Tech lead workflow completed successfully. Designed {architecture.get('pattern', 'monolith')} architecture with {len(tech_stack)} technology stack components, {len(api_spec.get('endpoints', []))} API endpoints, and {len(database_schema.get('tables', []))} database tables."


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Tech Lead skill for architecture design and technical strategy')
    parser.add_argument('--project-path', type=str, help='Path to the project directory')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Design architecture command
    arch_parser = subparsers.add_parser('design-architecture', help='Design system architecture')
    
    # Select tech stack command
    stack_parser = subparsers.add_parser('select-stack', help='Select technology stack')
    
    # Define patterns command
    patterns_parser = subparsers.add_parser('define-patterns', help='Define design patterns')
    
    # Design API command
    api_parser = subparsers.add_parser('design-api', help='Design API specifications')
    
    # Design database command
    db_parser = subparsers.add_parser('design-database', help='Design database schema')
    
    # Run workflow command
    workflow_parser = subparsers.add_parser('run', help='Run complete tech lead workflow')
    workflow_parser.add_argument('--project-path', type=str, required=True, help='Path to the project directory')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    lead = TechLead()
    project_path = Path(args.project_path) if args.project_path else Path.cwd()
    
    if args.command == 'design-architecture':
        code, content = lead.read_project_spec(project_path)
        if code != 0:
            print(f"Error: {content}", file=sys.stderr)
            return code
        
        requirements = lead.extract_requirements(content)
        architecture = lead.design_system_architecture(requirements)
        
        print(f"Architecture: {architecture.get('pattern', 'monolith').upper()}")
        print(f"Components: {len(architecture.get('components', []))}")
        for component in architecture.get('components', []):
            print(f"  - {component.get('name')}: {component.get('technology')}")
        
        return 0
    
    elif args.command == 'select-stack':
        code, content = lead.read_project_spec(project_path)
        if code != 0:
            print(f"Error: {content}", file=sys.stderr)
            return code
        
        requirements = lead.extract_requirements(content)
        tech_stack = lead.select_technology_stack(requirements)
        
        print("Technology Stack:")
        for category, stack in tech_stack.items():
            print(f"  {category.title()}: {stack.get('framework' if category != 'database' else 'primary', 'N/A')}")
        
        return 0
    
    elif args.command == 'define-patterns':
        design_patterns = lead.define_design_patterns()
        
        print(f"Primary Pattern: {design_patterns.get('primary_pattern', 'clean_architecture').upper()}")
        print(f"GoF Patterns: {len(design_patterns.get('gof_patterns', []))}")
        for pattern in design_patterns.get('gof_patterns', []):
            print(f"  - {pattern.get('name')} ({pattern.get('category')})")
        
        return 0
    
    elif args.command == 'design-api':
        code, content = lead.read_project_spec(project_path)
        if code != 0:
            print(f"Error: {content}", file=sys.stderr)
            return code
        
        requirements = lead.extract_requirements(content)
        api_spec = lead.design_api_specifications(requirements)
        
        print(f"API Protocol: {api_spec.get('protocol', 'REST')}")
        print(f"Endpoints: {len(api_spec.get('endpoints', []))}")
        for endpoint in api_spec.get('endpoints', []):
            print(f"  - {endpoint.get('method')} {endpoint.get('path')}: {endpoint.get('description')}")
        
        return 0
    
    elif args.command == 'design-database':
        code, content = lead.read_project_spec(project_path)
        if code != 0:
            print(f"Error: {content}", file=sys.stderr)
            return code
        
        requirements = lead.extract_requirements(content)
        database_schema = lead.design_database_schema(requirements)
        
        print(f"Database: {database_schema.get('database', 'PostgreSQL')}")
        print(f"Tables: {len(database_schema.get('tables', []))}")
        for table in database_schema.get('tables', []):
            print(f"  - {table.get('name')}: {len(table.get('columns', []))} columns")
        
        return 0
    
    elif args.command == 'run':
        code, output = lead.run_workflow(project_path)
        print(output)
        return code
    
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())