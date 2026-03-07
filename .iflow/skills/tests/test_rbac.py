#!/usr/bin/env python3
"""
Test suite for RBAC (Role-Based Access Control).
Tests role management, user management, permissions, policies, and access control.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import RBAC classes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.rbac import (
    Permission,
    ResourceType,
    Role,
    User,
    AccessPolicy,
    RBACManager,
    get_rbac_manager,
    require_permission
)
from utils.exceptions import IFlowError, ErrorCode


class TestPermission(unittest.TestCase):
    """Test Permission enum."""
    
    def test_permission_values(self):
        """Test permission enum values."""
        self.assertEqual(Permission.READ.value, "read")
        self.assertEqual(Permission.WRITE.value, "write")
        self.assertEqual(Permission.EXECUTE.value, "execute")
        self.assertEqual(Permission.DELETE.value, "delete")
        self.assertEqual(Permission.ADMIN.value, "admin")
        self.assertEqual(Permission.REVIEW.value, "review")
        self.assertEqual(Permission.APPROVE.value, "approve")
        self.assertEqual(Permission.MERGE.value, "merge")
        self.assertEqual(Permission.DEPLOY.value, "deploy")


class TestResourceType(unittest.TestCase):
    """Test ResourceType enum."""
    
    def test_resource_type_values(self):
        """Test resource type enum values."""
        self.assertEqual(ResourceType.WORKFLOW.value, "workflow")
        self.assertEqual(ResourceType.SKILL.value, "skill")
        self.assertEqual(ResourceType.PIPELINE.value, "pipeline")
        self.assertEqual(ResourceType.STATE_DOCUMENT.value, "state_document")
        self.assertEqual(ResourceType.CONFIGURATION.value, "configuration")
        self.assertEqual(ResourceType.GIT_OPERATION.value, "git_operation")
        self.assertEqual(ResourceType.REVIEW.value, "review")
        self.assertEqual(ResourceType.DEPLOYMENT.value, "deployment")


class TestRole(unittest.TestCase):
    """Test Role class."""
    
    def test_role_creation(self):
        """Test creating a role."""
        role = Role(
            name="admin",
            description="Administrator role",
            permissions={Permission.ADMIN, Permission.READ, Permission.WRITE}
        )
        
        self.assertEqual(role.name, "admin")
        self.assertEqual(role.description, "Administrator role")
        self.assertEqual(len(role.permissions), 3)
        self.assertIn(Permission.ADMIN, role.permissions)
    
    def test_role_to_dict(self):
        """Test converting role to dictionary."""
        role = Role(
            name="developer",
            description="Developer role",
            permissions={Permission.READ, Permission.WRITE, Permission.EXECUTE},
            resource_access={
                ResourceType.SKILL: {Permission.READ, Permission.EXECUTE},
                ResourceType.WORKFLOW: {Permission.READ, Permission.WRITE}
            }
        )
        
        role_dict = role.to_dict()
        
        self.assertEqual(role_dict["name"], "developer")
        self.assertEqual(role_dict["description"], "Developer role")
        self.assertEqual(len(role_dict["permissions"]), 3)
        self.assertIn("read", role_dict["permissions"])
        self.assertIn("skill", role_dict["resource_access"])
    
    def test_role_from_dict(self):
        """Test creating role from dictionary."""
        role_dict = {
            "name": "tester",
            "description": "Tester role",
            "permissions": ["read", "execute"],
            "resource_access": {
                "skill": ["read", "execute"],
                "workflow": ["read"]
            }
        }
        
        role = Role.from_dict(role_dict)
        
        self.assertEqual(role.name, "tester")
        self.assertEqual(role.description, "Tester role")
        self.assertIn(Permission.READ, role.permissions)
        self.assertIn(Permission.EXECUTE, role.permissions)
        self.assertIn(ResourceType.SKILL, role.resource_access)
    
    def test_role_has_permission_global(self):
        """Test checking global permissions."""
        role = Role(
            name="admin",
            permissions={Permission.ADMIN, Permission.READ, Permission.WRITE}
        )
        
        self.assertTrue(role.has_permission(Permission.READ))
        self.assertTrue(role.has_permission(Permission.WRITE))
        # ADMIN permission grants all permissions
        self.assertTrue(role.has_permission(Permission.DELETE))
    
    def test_role_has_permission_resource_specific(self):
        """Test checking resource-specific permissions."""
        role = Role(
            name="developer",
            permissions={Permission.READ},
            resource_access={
                ResourceType.SKILL: {Permission.READ, Permission.EXECUTE},
                ResourceType.WORKFLOW: {Permission.WRITE}
            }
        )
        
        self.assertTrue(role.has_permission(Permission.READ))  # Global
        self.assertTrue(role.has_permission(Permission.EXECUTE, ResourceType.SKILL))  # Resource-specific
        self.assertTrue(role.has_permission(Permission.WRITE, ResourceType.WORKFLOW))  # Resource-specific
        self.assertFalse(role.has_permission(Permission.EXECUTE, ResourceType.WORKFLOW))  # Not allowed
    
    def test_role_admin_has_all_permissions(self):
        """Test that admin role has all permissions."""
        role = Role(
            name="admin",
            permissions={Permission.ADMIN}
        )
        
        self.assertTrue(role.has_permission(Permission.READ))
        self.assertTrue(role.has_permission(Permission.WRITE))
        self.assertTrue(role.has_permission(Permission.EXECUTE))
        self.assertTrue(role.has_permission(Permission.DELETE))
        self.assertTrue(role.has_permission(Permission.ADMIN))
        self.assertTrue(role.has_permission(Permission.REVIEW))
        self.assertTrue(role.has_permission(Permission.APPROVE))
        self.assertTrue(role.has_permission(Permission.MERGE))
        self.assertTrue(role.has_permission(Permission.DEPLOY))


class TestUser(unittest.TestCase):
    """Test User class."""
    
    def test_user_creation(self):
        """Test creating a user."""
        user = User(
            username="john",
            email="john@example.com",
            roles={"developer", "tester"},
            attributes={"department": "engineering"}
        )
        
        self.assertEqual(user.username, "john")
        self.assertEqual(user.email, "john@example.com")
        self.assertEqual(len(user.roles), 2)
        self.assertIn("developer", user.roles)
        self.assertTrue(user.enabled)
    
    def test_user_to_dict(self):
        """Test converting user to dictionary."""
        user = User(
            username="jane",
            email="jane@example.com",
            roles={"admin"},
            attributes={"location": "US"},
            enabled=True
        )
        
        user_dict = user.to_dict()
        
        self.assertEqual(user_dict["username"], "jane")
        self.assertEqual(user_dict["email"], "jane@example.com")
        self.assertEqual(len(user_dict["roles"]), 1)
        self.assertEqual(user_dict["enabled"], True)
    
    def test_user_from_dict(self):
        """Test creating user from dictionary."""
        user_dict = {
            "username": "bob",
            "email": "bob@example.com",
            "roles": ["developer", "tester"],
            "attributes": {"level": "senior"},
            "enabled": True
        }
        
        user = User.from_dict(user_dict)
        
        self.assertEqual(user.username, "bob")
        self.assertEqual(user.email, "bob@example.com")
        self.assertIn("developer", user.roles)
        self.assertIn("tester", user.roles)
        self.assertTrue(user.enabled)
    
    def test_user_disabled_by_default(self):
        """Test that user is enabled by default."""
        user = User(username="test")
        self.assertTrue(user.enabled)


class TestAccessPolicy(unittest.TestCase):
    """Test AccessPolicy class."""
    
    def test_policy_creation(self):
        """Test creating an access policy."""
        policy = AccessPolicy(
            name="skill-access",
            description="Policy for skill access",
            resource_type=ResourceType.SKILL,
            resource_pattern="skill-*",
            required_permissions={Permission.READ, Permission.EXECUTE},
            allowed_roles={"developer", "tester"},
            denied_roles={"guest"},
            conditions={"environment": "production"}
        )
        
        self.assertEqual(policy.name, "skill-access")
        self.assertEqual(policy.resource_type, ResourceType.SKILL)
        self.assertEqual(policy.resource_pattern, "skill-*")
        self.assertIn(Permission.READ, policy.required_permissions)
        self.assertIn("developer", policy.allowed_roles)
    
    def test_policy_to_dict(self):
        """Test converting policy to dictionary."""
        policy = AccessPolicy(
            name="workflow-policy",
            resource_type=ResourceType.WORKFLOW,
            required_permissions={Permission.READ, Permission.WRITE},
            allowed_roles={"admin", "manager"}
        )
        
        policy_dict = policy.to_dict()
        
        self.assertEqual(policy_dict["name"], "workflow-policy")
        self.assertEqual(policy_dict["resource_type"], "workflow")
        self.assertIn("read", policy_dict["required_permissions"])
        self.assertIn("admin", policy_dict["allowed_roles"])
    
    def test_policy_from_dict(self):
        """Test creating policy from dictionary."""
        policy_dict = {
            "name": "git-policy",
            "description": "Git operations policy",
            "resource_type": "git_operation",
            "resource_pattern": "branch-*",
            "required_permissions": ["write", "merge"],
            "allowed_roles": ["developer", "senior-developer"],
            "denied_roles": ["intern"],
            "conditions": {}
        }
        
        policy = AccessPolicy.from_dict(policy_dict)
        
        self.assertEqual(policy.name, "git-policy")
        self.assertEqual(policy.resource_type, ResourceType.GIT_OPERATION)
        self.assertIn(Permission.WRITE, policy.required_permissions)
        self.assertIn("developer", policy.allowed_roles)
    
    def test_policy_matches_resource(self):
        """Test resource pattern matching."""
        policy = AccessPolicy(
            name="skill-policy",
            resource_type=ResourceType.SKILL,
            resource_pattern="skill-*"
        )
        
        self.assertTrue(policy.matches_resource("skill-a"))
        self.assertTrue(policy.matches_resource("skill-b"))
        self.assertFalse(policy.matches_resource("workflow-a"))
        self.assertTrue(policy.matches_resource("skill-test-123"))
    
    def test_policy_wildcard_pattern(self):
        """Test wildcard pattern matching."""
        policy = AccessPolicy(
            name="all-resources",
            resource_type=ResourceType.WORKFLOW,
            resource_pattern="*"
        )
        
        self.assertTrue(policy.matches_resource("workflow-a"))
        self.assertTrue(policy.matches_resource("workflow-b"))
        self.assertTrue(policy.matches_resource("any-resource"))


class TestRBACManager(unittest.TestCase):
    """Test RBACManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "rbac_config.json"
        self.rbac = RBACManager(config_file=self.config_file)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_rbac_manager_initialization(self):
        """Test RBAC manager initialization."""
        self.assertIsNotNone(self.rbac)
        # RBAC manager initializes with 5 default roles
        self.assertEqual(len(self.rbac.roles), 5)
        self.assertEqual(len(self.rbac.users), 0)
        self.assertEqual(len(self.rbac.policies), 0)
    
    def test_add_role(self):
        """Test adding a role."""
        role = Role(
            name="custom-role",
            description="Custom role",
            permissions={Permission.READ, Permission.WRITE}
        )
        
        initial_count = len(self.rbac.roles)
        self.rbac.add_role(role)
        
        # Should have one more role than initial
        self.assertEqual(len(self.rbac.roles), initial_count + 1)
        retrieved_role = self.rbac.get_role("custom-role")
        self.assertIsNotNone(retrieved_role)
        self.assertEqual(retrieved_role.name, "custom-role")
    
    def test_get_role_nonexistent(self):
        """Test getting a non-existent role."""
        role = self.rbac.get_role("nonexistent")
        self.assertIsNone(role)
    
    def test_add_user(self):
        """Test adding a user."""
        user = User(
            username="john",
            email="john@example.com",
            roles={"developer"}
        )
        
        self.rbac.add_user(user)
        
        self.assertEqual(len(self.rbac.users), 1)
        retrieved_user = self.rbac.get_user("john")
        self.assertIsNotNone(retrieved_user)
        self.assertEqual(retrieved_user.username, "john")
    
    def test_get_user_nonexistent(self):
        """Test getting a non-existent user."""
        user = self.rbac.get_user("nonexistent")
        self.assertIsNone(user)
    
    def test_assign_role(self):
        """Test assigning a role to a user."""
        # Create role and user
        role = Role(name="developer", permissions={Permission.READ})
        user = User(username="john")
        
        self.rbac.add_role(role)
        self.rbac.add_user(user)
        
        # Assign role
        result = self.rbac.assign_role("john", "developer")
        
        self.assertTrue(result)
        updated_user = self.rbac.get_user("john")
        self.assertIn("developer", updated_user.roles)
    
    def test_assign_role_user_not_found(self):
        """Test assigning role to non-existent user."""
        self.rbac.add_role(Role(name="developer", permissions={Permission.READ}))
        
        result = self.rbac.assign_role("nonexistent", "developer")
        
        self.assertFalse(result)
    
    def test_assign_role_role_not_found(self):
        """Test assigning non-existent role to user."""
        self.rbac.add_user(User(username="john"))
        
        result = self.rbac.assign_role("john", "nonexistent")
        
        self.assertFalse(result)
    
    def test_revoke_role(self):
        """Test revoking a role from a user."""
        # Create role and user with role
        role = Role(name="developer", permissions={Permission.READ})
        user = User(username="john", roles={"developer"})
        
        self.rbac.add_role(role)
        self.rbac.add_user(user)
        
        # Revoke role
        result = self.rbac.revoke_role("john", "developer")
        
        self.assertTrue(result)
        updated_user = self.rbac.get_user("john")
        self.assertNotIn("developer", updated_user.roles)
    
    def test_revoke_role_user_not_found(self):
        """Test revoking role from non-existent user."""
        result = self.rbac.revoke_role("nonexistent", "developer")
        self.assertFalse(result)
    
    def test_add_policy(self):
        """Test adding an access policy."""
        policy = AccessPolicy(
            name="skill-policy",
            resource_type=ResourceType.SKILL,
            required_permissions={Permission.READ},
            allowed_roles={"developer"}
        )
        
        self.rbac.add_policy(policy)
        
        self.assertEqual(len(self.rbac.policies), 1)
    
    def test_remove_policy(self):
        """Test removing an access policy."""
        policy = AccessPolicy(
            name="skill-policy",
            resource_type=ResourceType.SKILL,
            required_permissions={Permission.READ}
        )
        
        self.rbac.add_policy(policy)
        result = self.rbac.remove_policy("skill-policy")
        
        self.assertTrue(result)
        self.assertEqual(len(self.rbac.policies), 0)
    
    def test_remove_policy_nonexistent(self):
        """Test removing non-existent policy."""
        result = self.rbac.remove_policy("nonexistent")
        self.assertFalse(result)
    
    def test_check_permission_success(self):
        """Test successful permission check."""
        # Create role with read permission
        role = Role(name="reader", permissions={Permission.READ})
        self.rbac.add_role(role)
        
        # Create user with role
        user = User(username="john", roles={"reader"})
        self.rbac.add_user(user)
        
        # Check permission
        result = self.rbac.check_permission("john", Permission.READ, ResourceType.SKILL)
        
        self.assertTrue(result)
    
    def test_check_permission_no_permission(self):
        """Test permission check without permission."""
        # Create role without write permission
        role = Role(name="reader", permissions={Permission.READ})
        self.rbac.add_role(role)
        
        # Create user with role
        user = User(username="john", roles={"reader"})
        self.rbac.add_user(user)
        
        # Check permission
        result = self.rbac.check_permission("john", Permission.WRITE, ResourceType.SKILL)
        
        self.assertFalse(result)
    
    def test_check_permission_user_not_found(self):
        """Test permission check for non-existent user."""
        result = self.rbac.check_permission("nonexistent", Permission.READ, ResourceType.SKILL)
        self.assertFalse(result)
    
    def test_check_permission_disabled_user(self):
        """Test permission check for disabled user."""
        # Create role with permission
        role = Role(name="reader", permissions={Permission.READ})
        self.rbac.add_role(role)
        
        # Create disabled user
        user = User(username="john", roles={"reader"}, enabled=False)
        self.rbac.add_user(user)
        
        # Check permission
        result = self.rbac.check_permission("john", Permission.READ, ResourceType.SKILL)
        
        self.assertFalse(result)
    
    def test_check_permission_with_policy(self):
        """Test permission check with access policy."""
        # Create role
        role = Role(name="developer", permissions={Permission.READ})
        self.rbac.add_role(role)
        
        # Create user
        user = User(username="john", roles={"developer"})
        self.rbac.add_user(user)
        
        # Create policy
        policy = AccessPolicy(
            name="skill-policy",
            resource_type=ResourceType.SKILL,
            resource_pattern="skill-*",
            required_permissions={Permission.READ},
            allowed_roles={"developer"}
        )
        self.rbac.add_policy(policy)
        
        # Check permission with resource
        result = self.rbac.check_permission("john", Permission.READ, ResourceType.SKILL, "skill-a")
        
        self.assertTrue(result)
    
    def test_check_permission_denied_by_policy(self):
        """Test permission check denied by policy."""
        # Create role
        role = Role(name="guest", permissions={Permission.READ})
        self.rbac.add_role(role)
        
        # Create user
        user = User(username="john", roles={"guest"})
        self.rbac.add_user(user)
        
        # Create policy that denies guest role
        policy = AccessPolicy(
            name="restricted-policy",
            resource_type=ResourceType.SKILL,
            resource_pattern="secret-*",
            required_permissions={Permission.READ},
            denied_roles={"guest"}
        )
        self.rbac.add_policy(policy)
        
        # Check permission
        result = self.rbac.check_permission("john", Permission.READ, ResourceType.SKILL, "secret-data")
        
        self.assertFalse(result)
    
    def test_get_user_permissions(self):
        """Test getting all user permissions."""
        # Create roles
        reader_role = Role(name="reader", permissions={Permission.READ})
        writer_role = Role(name="writer", permissions={Permission.WRITE})
        self.rbac.add_role(reader_role)
        self.rbac.add_role(writer_role)
        
        # Create user with multiple roles
        user = User(username="john", roles={"reader", "writer"})
        self.rbac.add_user(user)
        
        # Get permissions
        permissions = self.rbac.get_user_permissions("john", ResourceType.SKILL)
        
        self.assertIn(Permission.READ, permissions)
        self.assertIn(Permission.WRITE, permissions)
    
    def test_get_accessible_resources(self):
        """Test getting accessible resources."""
        # Create role
        role = Role(name="developer", permissions={Permission.READ})
        self.rbac.add_role(role)
        
        # Create user
        user = User(username="john", roles={"developer"})
        self.rbac.add_user(user)
        
        # Create policies
        policy1 = AccessPolicy(
            name="skill-policy",
            resource_type=ResourceType.SKILL,
            resource_pattern="skill-*",
            required_permissions={Permission.READ},
            allowed_roles={"developer"}
        )
        policy2 = AccessPolicy(
            name="workflow-policy",
            resource_type=ResourceType.WORKFLOW,
            resource_pattern="workflow-*",
            required_permissions={Permission.READ},
            allowed_roles={"developer"}
        )
        self.rbac.add_policy(policy1)
        self.rbac.add_policy(policy2)
        
        # Get accessible resources
        resources = self.rbac.get_accessible_resources("john", ResourceType.SKILL, Permission.READ)
        
        self.assertEqual(len(resources), 1)
        self.assertIn("skill-*", resources)
    
    def test_config_persistence(self):
        """Test configuration persistence."""
        # Add custom role and user
        role = Role(name="custom-admin", permissions={Permission.ADMIN})
        user = User(username="custom-admin", roles={"custom-admin"})
        
        self.rbac.add_role(role)
        self.rbac.add_user(user)
        
        # Config should be saved
        self.assertTrue(self.config_file.exists())
        
        # Create new RBAC manager and load config
        new_rbac = RBACManager(config_file=self.config_file)
        
        # Verify data was loaded (5 default + 1 custom)
        self.assertEqual(len(new_rbac.roles), 6)
        self.assertEqual(len(new_rbac.users), 1)
        loaded_role = new_rbac.get_role("custom-admin")
        self.assertIsNotNone(loaded_role)


class TestRBACIntegration(unittest.TestCase):
    """Integration tests for RBAC functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "rbac_config.json"
        self.rbac = RBACManager(config_file=self.config_file)
        
        # Set up common roles
        self.rbac.add_role(Role(name="admin", permissions={Permission.ADMIN}))
        self.rbac.add_role(Role(name="developer", permissions={Permission.READ, Permission.WRITE}))
        self.rbac.add_role(Role(name="tester", permissions={Permission.READ}))
        
        # Set up users
        self.rbac.add_user(User(username="alice", roles={"admin"}))
        self.rbac.add_user(User(username="bob", roles={"developer"}))
        self.rbac.add_user(User(username="charlie", roles={"tester"}))
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_admin_has_full_access(self):
        """Test that admin has full access."""
        # Admin should have all permissions
        self.assertTrue(self.rbac.check_permission("alice", Permission.READ, ResourceType.WORKFLOW))
        self.assertTrue(self.rbac.check_permission("alice", Permission.WRITE, ResourceType.WORKFLOW))
        self.assertTrue(self.rbac.check_permission("alice", Permission.DELETE, ResourceType.WORKFLOW))
        self.assertTrue(self.rbac.check_permission("alice", Permission.EXECUTE, ResourceType.SKILL))
    
    def test_developer_has_limited_access(self):
        """Test that developer has limited access."""
        # Developer should have read and write but not delete
        self.assertTrue(self.rbac.check_permission("bob", Permission.READ, ResourceType.WORKFLOW))
        self.assertTrue(self.rbac.check_permission("bob", Permission.WRITE, ResourceType.WORKFLOW))
        self.assertFalse(self.rbac.check_permission("bob", Permission.DELETE, ResourceType.WORKFLOW))
        self.assertFalse(self.rbac.check_permission("bob", Permission.ADMIN, ResourceType.WORKFLOW))
    
    def test_tester_has_read_only_access(self):
        """Test that tester has read-only access."""
        # Tester should only have read permission
        self.assertTrue(self.rbac.check_permission("charlie", Permission.READ, ResourceType.WORKFLOW))
        self.assertFalse(self.rbac.check_permission("charlie", Permission.WRITE, ResourceType.WORKFLOW))
        self.assertFalse(self.rbac.check_permission("charlie", Permission.DELETE, ResourceType.WORKFLOW))
    
    def test_complex_permission_scenario(self):
        """Test complex permission scenario with multiple roles."""
        # Add additional role to user
        user = self.rbac.get_user("bob")
        user.roles.add("tester")
        
        # User should have combined permissions
        permissions = self.rbac.get_user_permissions("bob", ResourceType.WORKFLOW)
        
        self.assertIn(Permission.READ, permissions)
        self.assertIn(Permission.WRITE, permissions)
    
    def test_role_assignment_during_runtime(self):
        """Test assigning and revoking roles during runtime."""
        # User initially has developer role
        self.assertTrue(self.rbac.check_permission("bob", Permission.READ, ResourceType.WORKFLOW))
        
        # Revoke developer role
        self.rbac.revoke_role("bob", "developer")
        
        # User should no longer have access
        self.assertFalse(self.rbac.check_permission("bob", Permission.READ, ResourceType.WORKFLOW))
        
        # Assign tester role
        self.rbac.assign_role("bob", "tester")
        
        # User should have read access again
        self.assertTrue(self.rbac.check_permission("bob", Permission.READ, ResourceType.WORKFLOW))


class TestRBACDecorator(unittest.TestCase):
    """Test RBAC permission decorator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "rbac_config.json"
        self.rbac = RBACManager(config_file=self.config_file)
        
        # Set up role and user
        self.rbac.add_role(Role(name="admin", permissions={Permission.ADMIN}))
        self.rbac.add_user(User(username="admin", roles={"admin"}))
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_require_permission_decorator(self):
        """Test permission decorator."""
        @require_permission(Permission.ADMIN, ResourceType.WORKFLOW, rbac_manager=self.rbac)
        def admin_function(**kwargs):
            return "success"
        
        # Should succeed (call with username kwarg)
        result = admin_function(username="admin")
        self.assertEqual(result, "success")
    
    def test_require_permission_decorator_no_permission(self):
        """Test permission decorator without permission."""
        # Create user without admin permission
        self.rbac.add_role(Role(name="user", permissions={Permission.READ}))
        self.rbac.add_user(User(username="user", roles={"user"}))
        
        @require_permission(Permission.ADMIN, ResourceType.WORKFLOW, rbac_manager=self.rbac)
        def admin_function():
            return "success"
        
        # Should raise permission denied error
        with self.assertRaises(IFlowError) as context:
            admin_function(username="user")
        
        self.assertEqual(context.exception.code, ErrorCode.VALIDATION_FAILED)


if __name__ == '__main__':
    unittest.main()