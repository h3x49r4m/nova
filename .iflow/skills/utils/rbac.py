"""Role-Based Access Control (RBAC) - Manages permissions for workflows.

This module provides RBAC functionality for controlling access to
workflows, skills, and operations based on user roles and permissions.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from .exceptions import IFlowError, ErrorCode


class Permission(Enum):
    """Permission types."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"
    REVIEW = "review"
    APPROVE = "approve"
    MERGE = "merge"
    DEPLOY = "deploy"


class ResourceType(Enum):
    """Resource types that can be protected."""
    WORKFLOW = "workflow"
    SKILL = "skill"
    PIPELINE = "pipeline"
    STATE_DOCUMENT = "state_document"
    CONFIGURATION = "configuration"
    GIT_OPERATION = "git_operation"
    REVIEW = "review"
    DEPLOYMENT = "deployment"


@dataclass
class Role:
    """Represents a user role."""
    name: str
    description: str = ""
    permissions: Set[Permission] = field(default_factory=set)
    resource_access: Dict[ResourceType, Set[Permission]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "permissions": [p.value for p in self.permissions],
            "resource_access": {
                rt.value: [p.value for p in perms]
                for rt, perms in self.resource_access.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Role':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            permissions={Permission(p) for p in data.get("permissions", [])},
            resource_access={
                ResourceType(rt): {Permission(p) for p in perms}
                for rt, perms in data.get("resource_access", {}).items()
            }
        )
    
    def has_permission(
        self,
        permission: Permission,
        resource_type: Optional[ResourceType] = None
    ) -> bool:
        """
        Check if role has permission.
        
        Args:
            permission: Permission to check
            resource_type: Optional resource type
            
        Returns:
            True if has permission
        """
        # Check global permissions
        if permission in self.permissions:
            return True
        
        # Check resource-specific permissions
        if resource_type and resource_type in self.resource_access:
            if permission in self.resource_access[resource_type]:
                return True
        
        # Admin has all permissions
        if Permission.ADMIN in self.permissions:
            return True
        
        return False


@dataclass
class User:
    """Represents a user."""
    username: str
    email: str = ""
    roles: Set[str] = field(default_factory=set)
    attributes: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "username": self.username,
            "email": self.email,
            "roles": list(self.roles),
            "attributes": self.attributes,
            "enabled": self.enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create from dictionary."""
        return cls(
            username=data["username"],
            email=data.get("email", ""),
            roles=set(data.get("roles", [])),
            attributes=data.get("attributes", {}),
            enabled=data.get("enabled", True)
        )


@dataclass
class AccessPolicy:
    """Access policy for resources."""
    name: str
    resource_type: ResourceType
    description: str = ""
    resource_pattern: str = "*"
    required_permissions: Set[Permission] = field(default_factory=set)
    allowed_roles: Set[str] = field(default_factory=set)
    denied_roles: Set[str] = field(default_factory=set)
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "resource_type": self.resource_type.value,
            "resource_pattern": self.resource_pattern,
            "required_permissions": [p.value for p in self.required_permissions],
            "allowed_roles": list(self.allowed_roles),
            "denied_roles": list(self.denied_roles),
            "conditions": self.conditions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccessPolicy':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            resource_type=ResourceType(data["resource_type"]),
            resource_pattern=data.get("resource_pattern", "*"),
            required_permissions={Permission(p) for p in data.get("required_permissions", [])},
            allowed_roles=set(data.get("allowed_roles", [])),
            denied_roles=set(data.get("denied_roles", [])),
            conditions=data.get("conditions", {})
        )
    
    def matches_resource(self, resource: str) -> bool:
        """
        Check if policy matches resource.
        
        Args:
            resource: Resource identifier
            
        Returns:
            True if matches
        """
        import fnmatch
        return fnmatch.fnmatch(resource, self.resource_pattern)


class RBACManager:
    """Manages role-based access control."""
    
    def __init__(
        self,
        config_file: Optional[Path] = None,
        enable_persistence: bool = True
    ):
        """
        Initialize RBAC manager.
        
        Args:
            config_file: Configuration file path
            enable_persistence: Whether to persist configuration
        """
        self.config_file = config_file or (Path.cwd() / ".iflow" / "rbac" / "config.json")
        self.enable_persistence = enable_persistence
        
        self.roles: Dict[str, Role] = {}
        self.users: Dict[str, User] = {}
        self.policies: List[AccessPolicy] = []
        
        self._initialize_default_roles()
        
        if enable_persistence:
            self._load_config()
    
    def _load_config(self):
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                for role_data in data.get("roles", []):
                    role = Role.from_dict(role_data)
                    self.roles[role.name] = role
                
                for user_data in data.get("users", []):
                    user = User.from_dict(user_data)
                    self.users[user.username] = user
                
                for policy_data in data.get("policies", []):
                    policy = AccessPolicy.from_dict(policy_data)
                    self.policies.append(policy)
            
            except (json.JSONDecodeError, IOError):
                pass
    
    def _save_config(self):
        """Save configuration to file."""
        data = {
            "roles": [role.to_dict() for role in self.roles.values()],
            "users": [user.to_dict() for user in self.users.values()],
            "policies": [policy.to_dict() for policy in self.policies],
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save RBAC config: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def _initialize_default_roles(self):
        """Initialize default roles."""
        # Admin role - full access
        admin = Role(
            name="admin",
            description="Administrator with full access",
            permissions={Permission.ADMIN}
        )
        self.roles["admin"] = admin
        
        # Developer role
        developer = Role(
            name="developer",
            description="Developer with read/write access",
            permissions={Permission.READ, Permission.WRITE, Permission.EXECUTE},
            resource_access={
                ResourceType.WORKFLOW: {Permission.READ, Permission.EXECUTE},
                ResourceType.SKILL: {Permission.READ, Permission.EXECUTE},
                ResourceType.PIPELINE: {Permission.READ, Permission.EXECUTE},
                ResourceType.STATE_DOCUMENT: {Permission.READ, Permission.WRITE},
                ResourceType.GIT_OPERATION: {Permission.READ, Permission.EXECUTE}
            }
        )
        self.roles["developer"] = developer
        
        # Reviewer role
        reviewer = Role(
            name="reviewer",
            description="Code reviewer",
            permissions={Permission.READ, Permission.REVIEW},
            resource_access={
                ResourceType.REVIEW: {Permission.READ, Permission.REVIEW, Permission.APPROVE}
            }
        )
        self.roles["reviewer"] = reviewer
        
        # Deployer role
        deployer = Role(
            name="deployer",
            description="Deployment manager",
            permissions={Permission.READ, Permission.DEPLOY},
            resource_access={
                ResourceType.DEPLOYMENT: {Permission.READ, Permission.DEPLOY},
                ResourceType.PIPELINE: {Permission.READ}
            }
        )
        self.roles["deployer"] = deployer
        
        # Read-only role
        readonly = Role(
            name="readonly",
            description="Read-only access",
            permissions={Permission.READ}
        )
        self.roles["readonly"] = readonly
    
    def add_role(self, role: Role):
        """
        Add a role.
        
        Args:
            role: Role to add
        """
        self.roles[role.name] = role
        if self.enable_persistence:
            self._save_config()
    
    def get_role(self, role_name: str) -> Optional[Role]:
        """
        Get a role by name.
        
        Args:
            role_name: Role name
            
        Returns:
            Role or None
        """
        return self.roles.get(role_name)
    
    def add_user(self, user: User):
        """
        Add a user.
        
        Args:
            user: User to add
        """
        self.users[user.username] = user
        if self.enable_persistence:
            self._save_config()
    
    def get_user(self, username: str) -> Optional[User]:
        """
        Get a user by username.
        
        Args:
            username: Username
            
        Returns:
            User or None
        """
        return self.users.get(username)
    
    def assign_role(self, username: str, role_name: str) -> bool:
        """
        Assign role to user.
        
        Args:
            username: Username
            role_name: Role name
            
        Returns:
            True if successful
        """
        user = self.get_user(username)
        role = self.get_role(role_name)
        
        if not user or not role:
            return False
        
        user.roles.add(role_name)
        if self.enable_persistence:
            self._save_config()
        
        return True
    
    def revoke_role(self, username: str, role_name: str) -> bool:
        """
        Revoke role from user.
        
        Args:
            username: Username
            role_name: Role name
            
        Returns:
            True if successful
        """
        user = self.get_user(username)
        if not user:
            return False
        
        user.roles.discard(role_name)
        if self.enable_persistence:
            self._save_config()
        
        return True
    
    def add_policy(self, policy: AccessPolicy):
        """
        Add an access policy.
        
        Args:
            policy: Policy to add
        """
        self.policies.append(policy)
        if self.enable_persistence:
            self._save_config()
    
    def remove_policy(self, policy_name: str) -> bool:
        """
        Remove an access policy.
        
        Args:
            policy_name: Policy name
            
        Returns:
            True if policy was found and removed, False otherwise
        """
        initial_count = len(self.policies)
        self.policies = [p for p in self.policies if p.name != policy_name]
        
        # Check if a policy was actually removed
        if len(self.policies) < initial_count:
            if self.enable_persistence:
                self._save_config()
            return True
        
        return False
    
    def check_permission(
        self,
        username: str,
        permission: Permission,
        resource_type: ResourceType,
        resource: str = "*"
    ) -> bool:
        """
        Check if user has permission for resource.
        
        Args:
            username: Username
            permission: Permission to check
            resource_type: Type of resource
            resource: Resource identifier
            
        Returns:
            True if has permission
        """
        user = self.get_user(username)
        if not user or not user.enabled:
            return False
        
        # Check each role
        for role_name in user.roles:
            role = self.get_role(role_name)
            if not role:
                continue
            
            # Check if role has permission
            if role.has_permission(permission, resource_type):
                # Check policies
                policy_allowed = self._check_policies(
                    username, role_name, permission, resource_type, resource
                )
                if policy_allowed:
                    return True
        
        return False
    
    def _check_policies(
        self,
        username: str,
        role_name: str,
        permission: Permission,
        resource_type: ResourceType,
        resource: str
    ) -> bool:
        """
        Check access policies.
        
        Args:
            username: Username
            role_name: Role name
            permission: Permission
            resource_type: Resource type
            resource: Resource identifier
            
        Returns:
            True if allowed by policies
        """
        for policy in self.policies:
            # Check if policy applies
            if policy.resource_type != resource_type:
                continue
            
            if not policy.matches_resource(resource):
                continue
            
            # Check if permission is required
            if policy.required_permissions and permission not in policy.required_permissions:
                continue
            
            # Check denied roles
            if role_name in policy.denied_roles:
                return False
            
            # Check if role is in allowed list
            if policy.allowed_roles and role_name not in policy.allowed_roles:
                continue
            
            # Check conditions
            if policy.conditions:
                user = self.get_user(username)
                if not user:
                    return False
                
                for key, value in policy.conditions.items():
                    if user.attributes.get(key) != value:
                        return False
            
            return True
        
        # No matching policies, allow by default
        return True
    
    def get_user_permissions(
        self,
        username: str,
        resource_type: Optional[ResourceType] = None
    ) -> Set[Permission]:
        """
        Get all permissions for a user.
        
        Args:
            username: Username
            resource_type: Optional resource type filter
            
        Returns:
            Set of permissions
        """
        user = self.get_user(username)
        if not user or not user.enabled:
            return set()
        
        permissions = set()
        
        for role_name in user.roles:
            role = self.get_role(role_name)
            if not role:
                continue
            
            # Add global permissions
            permissions.update(role.permissions)
            
            # Add resource-specific permissions
            if resource_type and resource_type in role.resource_access:
                permissions.update(role.resource_access[resource_type])
        
        return permissions
    
    def get_accessible_resources(
        self,
        username: str,
        resource_type: ResourceType,
        permission: Permission
    ) -> List[str]:
        """
        Get resources accessible to user.
        
        Args:
            username: Username
            resource_type: Resource type
            permission: Required permission
            
        Returns:
            List of resource identifiers
        """
        resources = set()
        
        for policy in self.policies:
            if policy.resource_type != resource_type:
                continue
            
            if permission not in policy.required_permissions:
                continue
            
            user = self.get_user(username)
            if not user or not user.enabled:
                continue
            
            # Check if user has any allowed role
            if not any(role in user.roles for role in policy.allowed_roles):
                continue
            
            # Check if user has any denied role
            if any(role in user.roles for role in policy.denied_roles):
                continue
            
            # Add resource pattern
            if policy.resource_pattern != "*":
                resources.add(policy.resource_pattern)
        
        return list(resources)


# Global RBAC manager
_global_rbac: Optional[RBACManager] = None


def get_rbac_manager(
    config_file: Optional[Path] = None,
    enable_persistence: bool = True
) -> RBACManager:
    """
    Get or create global RBAC manager.
    
    Args:
        config_file: Configuration file path
        enable_persistence: Whether to persist configuration
        
    Returns:
        RBACManager instance
    """
    global _global_rbac
    
    if _global_rbac is None:
        _global_rbac = RBACManager(config_file, enable_persistence)
    
    return _global_rbac


def require_permission(
    permission: Permission,
    resource_type: ResourceType,
    resource: str = "*",
    rbac_manager: Optional[RBACManager] = None
):
    """
    Decorator for requiring permission.
    
    Args:
        permission: Required permission
        resource_type: Resource type
        resource: Resource identifier
        rbac_manager: Optional RBAC manager
        
    Returns:
        Decorator function
    """
    if rbac_manager is None:
        rbac_manager = get_rbac_manager()
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Get username from kwargs or assume current user
            username = kwargs.get("username", "anonymous")
            
            if not rbac_manager.check_permission(
                        username, permission, resource_type, resource
                    ):
                        raise IFlowError(
                            f"Permission denied: {permission.value} on {resource}",
                            ErrorCode.VALIDATION_FAILED
                        )            
            return func(*args, **kwargs)
        return wrapper
    return decorator