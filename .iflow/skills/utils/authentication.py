"""Authentication System - Token-based authentication for RBAC.

This module provides JWT-based authentication that integrates with the RBAC system
to provide secure user authentication and authorization.
"""

import json
import secrets
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

from .exceptions import IFlowError, ErrorCode, ErrorCategory
from .rbac import RBACManager, User


class AuthenticationError(IFlowError):
    """Authentication-related errors."""
    def __init__(self, message: str):
        super().__init__(message, ErrorCode.AUTHENTICATION_FAILED, ErrorCategory.PERMANENT)


class TokenManager:
    """Manages tokens for authentication."""
    
    def __init__(self, secret_key: Optional[str] = None, token_expiry_hours: int = 24):
        """
        Initialize token manager.
        
        Args:
            secret_key: Secret key for signing tokens (auto-generated if None)
            token_expiry_hours: Token expiry time in hours
        """
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.algorithm = "HS256" if JWT_AVAILABLE else "simple"
        self.token_expiry = timedelta(hours=token_expiry_hours)
        self.refresh_token_expiry = timedelta(days=7)
        
        # Track tokens
        self.access_tokens: Dict[str, Dict[str, Any]] = {}
        self.refresh_tokens: Dict[str, Dict[str, Any]] = {}
    
    def generate_token(self, user_id: str, username: str, roles: List[str]) -> str:
        """
        Generate an access token.
        
        Args:
            user_id: User ID
            username: Username
            roles: User roles
            
        Returns:
            Token string
        """
        if JWT_AVAILABLE:
            # Use JWT
            payload = {
                "user_id": user_id,
                "username": username,
                "roles": roles,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + self.token_expiry,
                "type": "access"
            }
            
            return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        else:
            # Use simple token system
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + self.token_expiry
            
            self.access_tokens[token] = {
                "user_id": user_id,
                "username": username,
                "roles": roles,
                "expires_at": expires_at.isoformat(),
                "type": "access"
            }
            
            return token
    
    def generate_refresh_token(self, user_id: str, username: str) -> str:
        """
        Generate a refresh token.
        
        Args:
            user_id: User ID
            username: Username
            
        Returns:
            Refresh token string
        """
        if JWT_AVAILABLE:
            token_id = secrets.token_urlsafe(32)
            
            payload = {
                "user_id": user_id,
                "username": username,
                "token_id": token_id,
                "iat": datetime.utcnow(),
                "exp": datetime.utcnow() + self.refresh_token_expiry,
                "type": "refresh"
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            # Store refresh token
            self.refresh_tokens[token_id] = {
                "user_id": user_id,
                "username": username,
                "expires_at": (datetime.utcnow() + self.refresh_token_expiry).isoformat()
            }
            
            return token
        else:
            # Use simple token system
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + self.refresh_token_expiry
            
            self.refresh_tokens[token] = {
                "user_id": user_id,
                "username": username,
                "expires_at": expires_at.isoformat(),
                "type": "refresh"
            }
            
            return token
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validate and decode a token.
        
        Args:
            token: Token string
            
        Returns:
            Decoded token payload
            
        Raises:
            AuthenticationError if token is invalid or expired
        """
        if JWT_AVAILABLE:
            # Use JWT validation
            try:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[self.algorithm]
                )
                
                # Check if refresh token is still valid
                if payload.get("type") == "refresh":
                    token_id = payload.get("token_id")
                    if token_id not in self.refresh_tokens:
                        raise AuthenticationError("Refresh token has been revoked")
                
                return payload
            
            except jwt.ExpiredSignatureError:
                raise AuthenticationError("Token has expired")
            except jwt.InvalidTokenError as e:
                raise AuthenticationError(f"Invalid token: {str(e)}")
        else:
            # Use simple token validation
            # Check access tokens
            if token in self.access_tokens:
                token_data = self.access_tokens[token]
                expires_at = datetime.fromisoformat(token_data["expires_at"])
                
                if datetime.utcnow() > expires_at:
                    del self.access_tokens[token]
                    raise AuthenticationError("Token has expired")
                
                return token_data
            
            # Check refresh tokens
            if token in self.refresh_tokens:
                token_data = self.refresh_tokens[token]
                expires_at = datetime.fromisoformat(token_data["expires_at"])
                
                if datetime.utcnow() > expires_at:
                    del self.refresh_tokens[token]
                    raise AuthenticationError("Token has expired")
                
                return token_data
            
            raise AuthenticationError("Invalid token")
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: Refresh token string
            
        Returns:
            Tuple of (new_access_token, new_refresh_token)
            
        Raises:
            AuthenticationError if refresh token is invalid
        """
        payload = self.validate_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid refresh token")
        
        user_id = payload["user_id"]
        username = payload["username"]
        roles = payload.get("roles", [])
        
        # Revoke old refresh token
        if JWT_AVAILABLE:
            token_id = payload.get("token_id")
            if token_id in self.refresh_tokens:
                del self.refresh_tokens[token_id]
        else:
            if refresh_token in self.refresh_tokens:
                del self.refresh_tokens[refresh_token]
        
        # Generate new tokens
        new_access_token = self.generate_token(user_id, username, roles)
        new_refresh_token = self.generate_refresh_token(user_id, username)
        
        return new_access_token, new_refresh_token
    
    def revoke_refresh_token(self, token_id: str) -> None:
        """
        Revoke a refresh token.
        
        Args:
            token_id: Token ID to revoke
        """
        if JWT_AVAILABLE:
            if token_id in self.refresh_tokens:
                del self.refresh_tokens[token_id]
        else:
            if token_id in self.refresh_tokens:
                del self.refresh_tokens[token_id]
    
    def revoke_all_user_tokens(self, user_id: str) -> None:
        """
        Revoke all refresh tokens for a user.
        
        Args:
            user_id: User ID
        """
        tokens_to_revoke = []
        
        if JWT_AVAILABLE:
            tokens_to_revoke = [
                token_id for token_id, data in self.refresh_tokens.items()
                if data["user_id"] == user_id
            ]
            
            for token_id in tokens_to_revoke:
                del self.refresh_tokens[token_id]
        else:
            tokens_to_revoke = [
                token_id for token_id, data in self.refresh_tokens.items()
                if data.get("user_id") == user_id
            ]
            
            for token_id in tokens_to_revoke:
                del self.refresh_tokens[token_id]


class Authenticator:
    """Authenticates users and manages credentials."""
    
    def __init__(
        self,
        rbac_manager: RBACManager,
        credentials_file: Optional[Path] = None
    ):
        """
        Initialize authenticator.
        
        Args:
            rbac_manager: RBAC manager instance
            credentials_file: File to store hashed credentials
        """
        self.rbac_manager = rbac_manager
        
        if credentials_file:
            self.credentials_file = credentials_file
        else:
            self.credentials_file = Path.cwd() / ".iflow" / "rbac" / "credentials.json"
        
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        self.credentials: Dict[str, Dict[str, Any]] = {}
        self._load_credentials()
    
    def _load_credentials(self) -> None:
        """Load user credentials from file."""
        if self.credentials_file.exists():
            try:
                with open(self.credentials_file, 'r') as f:
                    self.credentials = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.credentials = {}
    
    def _save_credentials(self) -> None:
        """Save user credentials to file."""
        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(self.credentials, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save credentials: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def _hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash a password with salt.
        
        Args:
            password: Plain text password
            salt: Optional salt (generated if None)
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use SHA-256 for hashing (in production, use bcrypt or argon2)
        salted_password = f"{salt}{password}".encode()
        hashed = hashlib.sha256(salted_password).hexdigest()
        
        return hashed, salt
    
    def _verify_password(self, password: str, hashed: str, salt: str) -> bool:
        """
        Verify a password against a hash.
        
        Args:
            password: Plain text password
            hashed: Hashed password
            salt: Salt used for hashing
            
        Returns:
            True if password matches
        """
        computed_hash, _ = self._hash_password(password, salt)
        return secrets.compare_digest(computed_hash, hashed)
    
    def create_user(
        self,
        username: str,
        password: str,
        email: str = "",
        roles: Optional[List[str]] = None
    ) -> User:
        """
        Create a new user with credentials.
        
        Args:
            username: Username
            password: Plain text password
            email: User email
            roles: List of roles to assign
            
        Returns:
            Created User object
            
        Raises:
            AuthenticationError if user already exists
        """
        if username in self.credentials:
            raise AuthenticationError(f"User '{username}' already exists")
        
        # Hash password
        hashed_password, salt = self._hash_password(password)
        
        # Store credentials
        self.credentials[username] = {
            "email": email,
            "password_hash": hashed_password,
            "salt": salt,
            "created_at": datetime.now().isoformat(),
            "last_login": None
        }
        
        self._save_credentials()
        
        # Create user in RBAC
        user = User(username=username, email=email, roles=set(roles or []))
        self.rbac_manager.add_user(user)
        
        return user
    
    def authenticate_user(
        self,
        username: str,
        password: str
    ) -> Tuple[User, Dict[str, Any]]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Tuple of (User, token_info)
            
        Raises:
            AuthenticationError if authentication fails
        """
        if username not in self.credentials:
            raise AuthenticationError("Invalid username or password")
        
        creds = self.credentials[username]
        
        # Verify password
        if not self._verify_password(password, creds["password_hash"], creds["salt"]):
            raise AuthenticationError("Invalid username or password")
        
        # Get user from RBAC
        user = self.rbac_manager.get_user(username)
        if not user:
            raise AuthenticationError(f"User '{username}' not found in RBAC system")
        
        if not user.enabled:
            raise AuthenticationError("User account is disabled")
        
        # Update last login
        creds["last_login"] = datetime.now().isoformat()
        self._save_credentials()
        
        return user, {
            "username": username,
            "email": creds.get("email", ""),
            "roles": list(user.roles),
            "last_login": creds["last_login"]
        }
    
    def change_password(
        self,
        username: str,
        old_password: str,
        new_password: str
    ) -> None:
        """
        Change a user's password.
        
        Args:
            username: Username
            old_password: Current password
            new_password: New password
            
        Raises:
            AuthenticationError if authentication fails
        """
        if username not in self.credentials:
            raise AuthenticationError("User not found")
        
        creds = self.credentials[username]
        
        # Verify old password
        if not self._verify_password(old_password, creds["password_hash"], creds["salt"]):
            raise AuthenticationError("Invalid current password")
        
        # Hash new password
        hashed_password, salt = self._hash_password(new_password)
        
        # Update credentials
        creds["password_hash"] = hashed_password
        creds["salt"] = salt
        creds["password_changed_at"] = datetime.now().isoformat()
        
        self._save_credentials()
    
    def delete_user(self, username: str) -> None:
        """
        Delete a user and their credentials.
        
        Args:
            username: Username to delete
        """
        if username in self.credentials:
            del self.credentials[username]
            self._save_credentials()
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get user information (excluding sensitive data).
        
        Args:
            username: Username
            
        Returns:
            User info dictionary or None
        """
        if username not in self.credentials:
            return None
        
        creds = self.credentials[username]
        user = self.rbac_manager.get_user(username)
        
        return {
            "username": username,
            "email": creds.get("email", ""),
            "roles": list(user.roles) if user else [],
            "created_at": creds.get("created_at"),
            "last_login": creds.get("last_login"),
            "enabled": user.enabled if user else False
        }


class AuthenticationSystem:
    """Complete authentication system with token management."""
    
    def __init__(
        self,
        rbac_manager: RBACManager,
        secret_key: Optional[str] = None,
        credentials_file: Optional[Path] = None,
        token_expiry_hours: int = 24
    ):
        """
        Initialize authentication system.
        
        Args:
            rbac_manager: RBAC manager instance
            secret_key: Optional secret key for tokens
            credentials_file: Optional credentials file path
            token_expiry_hours: Token expiry time in hours
        """
        self.rbac_manager = rbac_manager
        self.token_manager = TokenManager(secret_key, token_expiry_hours)
        self.authenticator = Authenticator(rbac_manager, credentials_file)
    
    def login(
        self,
        username: str,
        password: str
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Login a user and return tokens.
        
        Args:
            username: Username
            password: Plain text password
            
        Returns:
            Tuple of (access_token, refresh_token, user_info)
        """
        # Authenticate user
        user, user_info = self.authenticator.authenticate_user(username, password)
        
        # Generate tokens
        access_token = self.token_manager.generate_token(
            user_id=username,
            username=username,
            roles=list(user.roles)
        )
        
        refresh_token = self.token_manager.generate_refresh_token(
            user_id=username,
            username=username
        )
        
        return access_token, refresh_token, user_info
    
    def logout(self, refresh_token: str) -> None:
        """
        Logout a user by revoking their refresh token.
        
        Args:
            refresh_token: Refresh token to revoke
        """
        try:
            payload = self.token_manager.validate_token(refresh_token)
            
            # For JWT mode, use token_id
            if JWT_AVAILABLE and hasattr(self.token_manager, 'algorithm') and self.token_manager.algorithm == "HS256":
                token_id = payload.get("token_id")
                if token_id:
                    self.token_manager.revoke_refresh_token(token_id)
            else:
                # For simple token mode, use the token itself
                self.token_manager.revoke_refresh_token(refresh_token)
        except AuthenticationError:
            pass  # Token already invalid
    
    def refresh_tokens(self, refresh_token: str) -> Tuple[str, str]:
        """
        Refresh access and refresh tokens.
        
        Args:
            refresh_token: Current refresh token
            
        Returns:
            Tuple of (new_access_token, new_refresh_token)
        """
        return self.token_manager.refresh_access_token(refresh_token)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode a token.
        
        Args:
            token: JWT token
            
        Returns:
            Decoded token payload
            
        Raises:
            AuthenticationError if token is invalid
        """
        return self.token_manager.validate_token(token)
    
    def check_permission(
        self,
        token: str,
        permission: str,
        resource_type: str = "*"
    ) -> bool:
        """
        Check if a token holder has a specific permission.
        
        Args:
            token: JWT access token
            permission: Permission to check
            resource_type: Resource type
            
        Returns:
            True if permission is granted
        """
        from .rbac import Permission as RBACPermission, ResourceType as RBACResourceType
        
        try:
            payload = self.verify_token(token)
            username = payload["username"]
            
            return self.rbac_manager.check_permission(
                username=username,
                permission=RBACPermission(permission.lower()),
                resource_type=RBACResourceType(resource_type)
            )
        except AuthenticationError:
            return False