"""Authentication System - Token-based authentication for RBAC.

This module provides JWT-based authentication that integrates with the RBAC system
to provide secure user authentication and authorization.
"""

import json
import secrets
import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

from .exceptions import IFlowError, ErrorCode, ErrorCategory
from .rbac import RBACManager, User


class AuthenticationError(IFlowError):
    """Authentication-related errors."""
    def __init__(self, message: str):
        super().__init__(message, ErrorCode.AUTHENTICATION_FAILED, ErrorCategory.PERMANENT)


class RateLimiter:
    """Rate limiter for authentication operations to prevent brute force attacks."""
    
    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        """
        Initialize rate limiter.

        Args:
            max_attempts: Maximum number of attempts allowed in the time window
            window_seconds: Time window in seconds (default: 5 minutes)
        """
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.attempts: Dict[str, List[datetime]] = defaultdict(list)
        self.blocked_until: Dict[str, datetime] = {}
    
    def check_rate_limit(self, identifier: str) -> Tuple[bool, Optional[int]]:
        """
        Check if the identifier has exceeded the rate limit.

        Args:
            identifier: Unique identifier (e.g., username, IP address)

        Returns:
            Tuple of (is_allowed, remaining_attempts)
        """
        now = datetime.now(timezone.utc)

        # Check if currently blocked
        if identifier in self.blocked_until:
            if now < self.blocked_until[identifier]:
                return False, 0
            else:
                # Block expired, remove it
                del self.blocked_until[identifier]
        
        # Clean up old attempts outside the time window
        self.attempts[identifier] = [
            attempt_time for attempt_time in self.attempts[identifier]
            if (now - attempt_time).total_seconds() < self.window_seconds
        ]
        
        # Check if limit exceeded
        current_attempts = len(self.attempts[identifier])
        if current_attempts >= self.max_attempts:
            # Block for the window duration
            self.blocked_until[identifier] = now + timedelta(seconds=self.window_seconds)
            return False, 0
        
        return True, self.max_attempts - current_attempts
    
    def record_attempt(self, identifier: str) -> None:
        """
        Record an authentication attempt.

        Args:
            identifier: Unique identifier (e.g., username, IP address)
        """
        self.attempts[identifier].append(datetime.now(timezone.utc))
    
    def reset_attempts(self, identifier: str) -> None:
        """
        Reset attempts for a successful authentication.

        Args:
            identifier: Unique identifier (e.g., username, IP address)
        """
        if identifier in self.attempts:
            del self.attempts[identifier]
        if identifier in self.blocked_until:
            del self.blocked_until[identifier]
    
    def get_block_time_remaining(self, identifier: str) -> Optional[int]:
        """
        Get the remaining block time in seconds.

        Args:
            identifier: Unique identifier

        Returns:
            Remaining seconds until block expires, or None if not blocked
        """
        if identifier in self.blocked_until:
            remaining = (self.blocked_until[identifier] - datetime.utcnow()).total_seconds()
            return max(0, int(remaining))
        return None


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
            expires_at = datetime.now(timezone.utc) + self.token_expiry

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
            expires_at = datetime.now(timezone.utc) + self.refresh_token_expiry

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

                if datetime.now(timezone.utc) > expires_at:
                    del self.access_tokens[token]
                    raise AuthenticationError("Token has expired")

                return token_data
            
            # Check refresh tokens
            if token in self.refresh_tokens:
                token_data = self.refresh_tokens[token]
                expires_at = datetime.fromisoformat(token_data["expires_at"])

                if datetime.now(timezone.utc) > expires_at:
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
        Hash a password with salt using bcrypt.
        
        Args:
            password: Plain text password
            salt: Optional salt (generated if None)
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if BCRYPT_AVAILABLE:
            # Use bcrypt for secure password hashing
            if salt is None:
                salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8'), salt.decode('utf-8')
        else:
            # Fallback to SHA-256 if bcrypt not available
            if salt is None:
                salt = secrets.token_hex(16)
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
        if BCRYPT_AVAILABLE:
            # Use bcrypt's built-in verification
            try:
                return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
            except (ValueError, TypeError):
                return False
        else:
            # Fallback to SHA-256 verification
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
            AuthenticationError if user already exists or validation fails
        """
        # Validate username
        if not username or not isinstance(username, str):
            raise AuthenticationError("Username must be a non-empty string")
        
        if len(username) < 3 or len(username) > 50:
            raise AuthenticationError("Username must be between 3 and 50 characters")
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            raise AuthenticationError("Username must contain only alphanumeric characters, hyphens, and underscores")
        
        if username in self.credentials:
            raise AuthenticationError(f"User '{username}' already exists")
        
        # Validate password
        if not password or not isinstance(password, str):
            raise AuthenticationError("Password must be a non-empty string")
        
        if len(password) < 8:
            raise AuthenticationError("Password must be at least 8 characters long")
        
        # Validate email if provided
        if email:
            if not isinstance(email, str):
                raise AuthenticationError("Email must be a string")
            
            # Basic email validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                raise AuthenticationError("Invalid email format")
        
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
        token_expiry_hours: int = 24,
        max_login_attempts: int = 5,
        login_window_seconds: int = 300
    ):
        """
        Initialize authentication system.
        
        Args:
            rbac_manager: RBAC manager instance
            secret_key: Optional secret key for tokens
            credentials_file: Optional credentials file path
            token_expiry_hours: Token expiry time in hours
            max_login_attempts: Maximum login attempts before blocking
            login_window_seconds: Time window for login attempts
        """
        self.rbac_manager = rbac_manager
        self.token_manager = TokenManager(secret_key, token_expiry_hours)
        self.authenticator = Authenticator(rbac_manager, credentials_file)
        self.rate_limiter = RateLimiter(max_login_attempts, login_window_seconds)
    
    def login(
        self,
        username: str,
        password: str
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Login a user and return tokens with rate limiting.

        Args:
            username: Username
            password: Plain text password

        Returns:
            Tuple of (access_token, refresh_token, user_info)

        Raises:
            AuthenticationError if rate limit exceeded or authentication fails
        """
        # Check rate limit
        is_allowed, remaining_attempts = self.rate_limiter.check_rate_limit(username)
        
        if not is_allowed:
            block_time_remaining = self.rate_limiter.get_block_time_remaining(username)
            raise AuthenticationError(
                f"Too many failed login attempts. Please try again in {block_time_remaining} seconds."
            )
        
        # Record attempt before authentication
        self.rate_limiter.record_attempt(username)
        
        try:
            # Authenticate user
            user, user_info = self.authenticator.authenticate_user(username, password)
            
            # Reset attempts on successful authentication
            self.rate_limiter.reset_attempts(username)
            
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
            
        except AuthenticationError:
            # Keep the attempt recorded on failed authentication
            remaining = self.rate_limiter.max_attempts - len(self.rate_limiter.attempts[username])
            raise AuthenticationError(
                f"Invalid username or password. {remaining} attempt(s) remaining."
            )
    
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