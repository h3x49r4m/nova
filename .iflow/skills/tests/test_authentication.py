#!/usr/bin/env python3
"""Test suite for authentication system.

Tests token-based authentication and integration with RBAC.
"""

import tempfile
import unittest
from pathlib import Path

# Import authentication classes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.authentication import (
    AuthenticationSystem,
    Authenticator,
    TokenManager,
    AuthenticationError
)
from utils.rbac import RBACManager, Role, Permission


class TestTokenManager(unittest.TestCase):
    """Test token manager functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.token_manager = TokenManager()
    
    def test_generate_and_validate_token(self):
        """Test generating and validating a token."""
        token = self.token_manager.generate_token(
            user_id="user1",
            username="testuser",
            roles=["admin"]
        )
        
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)
        
        # Validate token
        payload = self.token_manager.validate_token(token)
        self.assertEqual(payload["user_id"], "user1")
        self.assertEqual(payload["username"], "testuser")
        self.assertEqual(payload["roles"], ["admin"])
        self.assertEqual(payload["type"], "access")
    
    def test_generate_refresh_token(self):
        """Test generating a refresh token."""
        token = self.token_manager.generate_refresh_token(
            user_id="user1",
            username="testuser"
        )
        
        self.assertIsInstance(token, str)
        
        # Validate refresh token
        payload = self.token_manager.validate_token(token)
        self.assertEqual(payload["user_id"], "user1")
        self.assertEqual(payload["username"], "testuser")
        self.assertEqual(payload["type"], "refresh")
        # token_id is only available in JWT mode
        if hasattr(self.token_manager, 'algorithm') and self.token_manager.algorithm == "HS256":
            self.assertIn("token_id", payload)
    
    def test_refresh_access_token(self):
        """Test refreshing an access token."""
        # Generate initial tokens
        access_token = self.token_manager.generate_token(
            user_id="user1",
            username="testuser",
            roles=["admin"]
        )
        refresh_token = self.token_manager.generate_refresh_token(
            user_id="user1",
            username="testuser"
        )
        
        # Refresh tokens
        new_access, new_refresh = self.token_manager.refresh_access_token(refresh_token)
        
        self.assertIsInstance(new_access, str)
        self.assertIsInstance(new_refresh, str)
        self.assertNotEqual(access_token, new_access)
        self.assertNotEqual(refresh_token, new_refresh)
        
        # Validate new tokens
        payload = self.token_manager.validate_token(new_access)
        self.assertEqual(payload["username"], "testuser")
    
    def test_revoke_refresh_token(self):
        """Test revoking a refresh token."""
        refresh_token = self.token_manager.generate_refresh_token(
            user_id="user1",
            username="testuser"
        )
        
        # Get token ID (only for JWT mode)
        payload = self.token_manager.validate_token(refresh_token)
        if hasattr(self.token_manager, 'algorithm') and self.token_manager.algorithm == "HS256":
            token_id = payload["token_id"]
        else:
            token_id = refresh_token
        
        # Revoke token
        self.token_manager.revoke_refresh_token(token_id)
        
        # Try to validate - should fail
        with self.assertRaises(AuthenticationError):
            self.token_manager.validate_token(refresh_token)
    
    def test_revoke_all_user_tokens(self):
        """Test revoking all tokens for a user."""
        # Generate multiple tokens for the same user
        token1 = self.token_manager.generate_refresh_token("user1", "testuser")
        token2 = self.token_manager.generate_refresh_token("user1", "testuser")
        token3 = self.token_manager.generate_refresh_token("user2", "otheruser")
        
        # Revoke all tokens for user1
        self.token_manager.revoke_all_user_tokens("user1")
        
        # user1 tokens should be invalid
        with self.assertRaises(AuthenticationError):
            self.token_manager.validate_token(token1)
        with self.assertRaises(AuthenticationError):
            self.token_manager.validate_token(token2)
        
        # user2 token should still be valid
        payload = self.token_manager.validate_token(token3)
        self.assertEqual(payload["username"], "otheruser")


class TestAuthenticator(unittest.TestCase):
    """Test authenticator functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.credentials_file = Path(self.temp_dir) / "credentials.json"
        
        # Create RBAC manager
        self.rbac_manager = RBACManager(
            config_file=None,
            enable_persistence=False
        )
        
        self.authenticator = Authenticator(
            rbac_manager=self.rbac_manager,
            credentials_file=self.credentials_file
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_create_user(self):
        """Test creating a new user."""
        user = self.authenticator.create_user(
            username="testuser",
            password="password123",
            email="test@example.com",
            roles=["admin"]
        )
        
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertIn("admin", user.roles)
        self.assertIn("testuser", self.authenticator.credentials)
    
    def test_create_duplicate_user(self):
        """Test creating a duplicate user."""
        self.authenticator.create_user(
            username="testuser",
            password="password123"
        )
        
        with self.assertRaises(AuthenticationError):
            self.authenticator.create_user(
                username="testuser",
                password="password456"
            )
    
    def test_authenticate_user(self):
        """Test user authentication."""
        # Create user
        self.authenticator.create_user(
            username="testuser",
            password="password123",
            email="test@example.com"
        )
        
        # Authenticate with correct password
        user, user_info = self.authenticator.authenticate_user("testuser", "password123")
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user_info["email"], "test@example.com")
        
        # Authenticate with wrong password
        with self.assertRaises(AuthenticationError):
            self.authenticator.authenticate_user("testuser", "wrongpassword")
        
        # Authenticate non-existent user
        with self.assertRaises(AuthenticationError):
            self.authenticator.authenticate_user("nonexistent", "password123")
    
    def test_change_password(self):
        """Test changing a user's password."""
        # Create user
        self.authenticator.create_user(
            username="testuser",
            password="password123"
        )
        
        # Change password
        self.authenticator.change_password("testuser", "password123", "newpassword456")
        
        # Old password should not work
        with self.assertRaises(AuthenticationError):
            self.authenticator.authenticate_user("testuser", "password123")
        
        # New password should work
        user, _ = self.authenticator.authenticate_user("testuser", "newpassword456")
        self.assertEqual(user.username, "testuser")
    
    def test_change_password_wrong_old_password(self):
        """Test changing password with wrong old password."""
        self.authenticator.create_user(
            username="testuser",
            password="password123"
        )
        
        with self.assertRaises(AuthenticationError):
            self.authenticator.change_password("testuser", "wrongpassword", "newpassword456")
    
    def test_delete_user(self):
        """Test deleting a user."""
        # Create user
        self.authenticator.create_user(
            username="testuser",
            password="password123"
        )
        
        # Delete user
        self.authenticator.delete_user("testuser")
        
        # User should not exist
        self.assertNotIn("testuser", self.authenticator.credentials)
        
        # Should not be able to authenticate
        with self.assertRaises(AuthenticationError):
            self.authenticator.authenticate_user("testuser", "password123")
    
    def test_get_user_info(self):
        """Test getting user information."""
        self.authenticator.create_user(
            username="testuser",
            password="password123",
            email="test@example.com",
            roles=["admin"]
        )
        
        user_info = self.authenticator.get_user_info("testuser")
        
        self.assertEqual(user_info["username"], "testuser")
        self.assertEqual(user_info["email"], "test@example.com")
        self.assertIn("admin", user_info["roles"])
        self.assertNotIn("password_hash", user_info)
        self.assertNotIn("salt", user_info)
    
    def test_get_nonexistent_user_info(self):
        """Test getting info for non-existent user."""
        user_info = self.authenticator.get_user_info("nonexistent")
        self.assertIsNone(user_info)


class TestAuthenticationSystem(unittest.TestCase):
    """Test complete authentication system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.credentials_file = Path(self.temp_dir) / "credentials.json"
        
        # Create RBAC manager
        self.rbac_manager = RBACManager(
            config_file=None,
            enable_persistence=False
        )
        
        # Create admin role
        admin_role = Role(
            name="admin",
            description="Administrator",
            permissions={Permission.ADMIN}
        )
        self.rbac_manager.add_role(admin_role)
        
        # Create user role
        user_role = Role(
            name="user",
            description="Regular user",
            permissions={Permission.READ}
        )
        self.rbac_manager.add_role(user_role)
        
        self.auth_system = AuthenticationSystem(
            rbac_manager=self.rbac_manager,
            credentials_file=self.credentials_file
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_login_flow(self):
        """Test complete login flow."""
        # Create user
        self.auth_system.authenticator.create_user(
            username="testuser",
            password="password123",
            roles=["user"]
        )
        
        # Login
        access_token, refresh_token, user_info = self.auth_system.login(
            "testuser",
            "password123"
        )
        
        self.assertIsInstance(access_token, str)
        self.assertIsInstance(refresh_token, str)
        self.assertEqual(user_info["username"], "testuser")
        self.assertIn("user", user_info["roles"])
        
        # Verify access token
        payload = self.auth_system.verify_token(access_token)
        self.assertEqual(payload["username"], "testuser")
    
    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials."""
        self.auth_system.authenticator.create_user(
            username="testuser",
            password="password123"
        )
        
        with self.assertRaises(AuthenticationError):
            self.auth_system.login("testuser", "wrongpassword")
    
    def test_check_permission_with_token(self):
        """Test checking permissions using a token."""
        # Create admin user
        self.auth_system.authenticator.create_user(
            username="adminuser",
            password="password123",
            roles=["admin"]
        )
        
        # Login
        access_token, _, _ = self.auth_system.login("adminuser", "password123")
        
        # Check admin permission
        has_permission = self.auth_system.check_permission(
            access_token,
            "admin",
            "workflow"
        )
        self.assertTrue(has_permission)
    
    def test_token_refresh_flow(self):
        """Test token refresh flow."""
        # Create user
        self.auth_system.authenticator.create_user(
            username="testuser",
            password="password123",
            roles=["user"]
        )
        
        # Login
        access_token, refresh_token, _ = self.auth_system.login("testuser", "password123")
        
        # Refresh tokens
        new_access, new_refresh = self.auth_system.refresh_tokens(refresh_token)
        
        # New tokens should be different
        self.assertNotEqual(access_token, new_access)
        self.assertNotEqual(refresh_token, new_refresh)
        
        # New access token should be valid
        payload = self.auth_system.verify_token(new_access)
        self.assertEqual(payload["username"], "testuser")
    
    def test_logout_flow(self):
        """Test logout flow."""
        # Create user
        self.auth_system.authenticator.create_user(
            username="testuser",
            password="password123",
            roles=["user"]
        )
        
        # Login
        _, refresh_token, _ = self.auth_system.login("testuser", "password123")
        
        # Logout
        self.auth_system.logout(refresh_token)
        
        # Try to refresh with revoked token - should fail
        with self.assertRaises(AuthenticationError):
            self.auth_system.refresh_tokens(refresh_token)


if __name__ == '__main__':
    unittest.main()