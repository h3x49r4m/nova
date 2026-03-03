"""Schema Version Manager - Manages schema versions and migrations.

This module provides functionality for managing schema versions,
tracking changes, and performing migrations between versions.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .exceptions import IFlowError, ErrorCode


class MigrationType(Enum):
    """Types of schema migrations."""
    ADD_FIELD = "add_field"
    REMOVE_FIELD = "remove_field"
    RENAME_FIELD = "rename_field"
    CHANGE_TYPE = "change_type"
    ADD_CONSTRAINT = "add_constraint"
    REMOVE_CONSTRAINT = "remove_constraint"
    CHANGE_DEFAULT = "change_default"
    BACKWARD_INCOMPATIBLE = "backward_incompatible"


@dataclass
class SchemaVersion:
    """Represents a schema version."""
    version: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""
    changes: List[str] = field(default_factory=list)
    backward_compatible: bool = True
    migration_required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "created_at": self.created_at,
            "description": self.description,
            "changes": self.changes,
            "backward_compatible": self.backward_compatible,
            "migration_required": self.migration_required
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SchemaVersion':
        """Create from dictionary."""
        return cls(
            version=data["version"],
            created_at=data.get("created_at", datetime.now().isoformat()),
            description=data.get("description", ""),
            changes=data.get("changes", []),
            backward_compatible=data.get("backward_compatible", True),
            migration_required=data.get("migration_required", False)
        )


@dataclass
class Migration:
    """Represents a schema migration."""
    from_version: str
    to_version: str
    migration_type: MigrationType
    field_name: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "migration_type": self.migration_type.value,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "description": self.description,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Migration':
        """Create from dictionary."""
        return cls(
            from_version=data["from_version"],
            to_version=data["to_version"],
            migration_type=MigrationType(data["migration_type"]),
            field_name=data.get("field_name"),
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            description=data.get("description", ""),
            created_at=data.get("created_at", datetime.now().isoformat())
        )


class SchemaVersionManager:
    """Manages schema versions and migrations."""
    
    def __init__(
        self,
        repo_root: Path,
        schema_dir: Optional[Path] = None
    ):
        """
        Initialize the schema version manager.
        
        Args:
            repo_root: Repository root directory
            schema_dir: Directory for schema version files
        """
        self.repo_root = repo_root
        self.schema_dir = schema_dir or (repo_root / ".iflow" / "schemas" / "versions")
        self.schema_dir.mkdir(parents=True, exist_ok=True)
        
        self.versions_file = self.schema_dir / "versions.json"
        self.migrations_file = self.schema_dir / "migrations.json"
        
        self.versions: Dict[str, SchemaVersion] = {}
        self.migrations: List[Migration] = []
        self.migration_functions: Dict[str, Callable] = {}
        
        self._load_versions()
        self._load_migrations()
    
    def _load_versions(self):
        """Load schema versions from file."""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, 'r') as f:
                    data = json.load(f)
                
                for version_data in data.get("versions", []):
                    version = SchemaVersion.from_dict(version_data)
                    self.versions[version.version] = version
            except (json.JSONDecodeError, IOError):
                pass
    
    def _load_migrations(self):
        """Load migrations from file."""
        if self.migrations_file.exists():
            try:
                with open(self.migrations_file, 'r') as f:
                    data = json.load(f)
                
                for migration_data in data.get("migrations", []):
                    migration = Migration.from_dict(migration_data)
                    self.migrations.append(migration)
            except (json.JSONDecodeError, IOError):
                pass
    
    def _save_versions(self):
        """Save schema versions to file."""
        data = {
            "versions": [v.to_dict() for v in self.versions.values()],
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            with open(self.versions_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save versions: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def _save_migrations(self):
        """Save migrations to file."""
        data = {
            "migrations": [m.to_dict() for m in self.migrations],
            "last_updated": datetime.now().isoformat()
        }
        
        try:
            with open(self.migrations_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save migrations: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def register_version(
        self,
        version: str,
        description: str = "",
        changes: Optional[List[str]] = None,
        backward_compatible: bool = True
    ) -> SchemaVersion:
        """
        Register a new schema version.
        
        Args:
            version: Version string (semantic version)
            description: Description of the version
            changes: List of changes in this version
            backward_compatible: Whether this version is backward compatible
            
        Returns:
            Created SchemaVersion object
        """
        if version in self.versions:
            raise IFlowError(
                f"Version {version} already exists",
                ErrorCode.ALREADY_EXISTS
            )
        
        schema_version = SchemaVersion(
            version=version,
            description=description,
            changes=changes or [],
            backward_compatible=backward_compatible,
            migration_required=not backward_compatible
        )
        
        self.versions[version] = schema_version
        self._save_versions()
        
        return schema_version
    
    def get_version(self, version: str) -> Optional[SchemaVersion]:
        """
        Get a schema version.
        
        Args:
            version: Version string
            
        Returns:
            SchemaVersion or None
        """
        return self.versions.get(version)
    
    def get_latest_version(self) -> Optional[str]:
        """
        Get the latest schema version.
        
        Returns:
            Version string or None
        """
        if not self.versions:
            return None
        
        # Sort versions and return the latest
        sorted_versions = sorted(
            self.versions.keys(),
            key=lambda v: [int(x) for x in v.split(".")]
        )
        
        return sorted_versions[-1]
    
    def register_migration(
        self,
        from_version: str,
        to_version: str,
        migration_type: MigrationType,
        field_name: Optional[str] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        description: str = "",
        migration_function: Optional[Callable] = None
    ) -> Migration:
        """
        Register a migration.
        
        Args:
            from_version: Source version
            to_version: Target version
            migration_type: Type of migration
            field_name: Name of affected field
            old_value: Old value
            new_value: New value
            description: Description of the migration
            migration_function: Function to perform the migration
            
        Returns:
            Created Migration object
        """
        migration = Migration(
            from_version=from_version,
            to_version=to_version,
            migration_type=migration_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            description=description
        )
        
        self.migrations.append(migration)
        
        # Register migration function if provided
        if migration_function:
            migration_key = f"{from_version}_to_{to_version}"
            self.migration_functions[migration_key] = migration_function
        
        self._save_migrations()
        
        return migration
    
    def get_migration_path(
        self,
        from_version: str,
        to_version: str
    ) -> List[Migration]:
        """
        Get the migration path between versions.
        
        Args:
            from_version: Source version
            to_version: Target version
            
        Returns:
            List of migrations in order
        """
        path = []
        
        for migration in self.migrations:
            if migration.from_version == from_version and migration.to_version == to_version:
                path.append(migration)
            elif migration.from_version == from_version:
                # Check if this migration can lead to the target
                sub_path = self.get_migration_path(migration.to_version, to_version)
                if sub_path:
                    path.append(migration)
                    path.extend(sub_path)
        
        return path
    
    def can_migrate(
        self,
        from_version: str,
        to_version: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if migration is possible.
        
        Args:
            from_version: Source version
            to_version: Target version
            
        Returns:
            Tuple of (can_migrate, error_message)
        """
        if from_version not in self.versions:
            return False, f"Source version {from_version} not found"
        
        if to_version not in self.versions:
            return False, f"Target version {to_version} not found"
        
        path = self.get_migration_path(from_version, to_version)
        
        if not path:
            return False, f"No migration path from {from_version} to {to_version}"
        
        return True, None
    
    def migrate(
        self,
        data: Dict[str, Any],
        from_version: str,
        to_version: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Migrate data from one version to another.
        
        Args:
            data: Data to migrate
            from_version: Source version
            to_version: Target version
            
        Returns:
            Tuple of (success, message, migrated_data)
        """
        can_migrate, error = self.can_migrate(from_version, to_version)
        
        if not can_migrate:
            return False, error, data
        
        path = self.get_migration_path(from_version, to_version)
        migrated_data = data.copy()
        
        for migration in path:
            migration_key = f"{migration.from_version}_to_{migration.to_version}"
            
            # Use custom migration function if available
            if migration_key in self.migration_functions:
                try:
                    migrated_data = self.migration_functions[migration_key](migrated_data)
                except Exception as e:
                    return False, f"Migration failed: {str(e)}", data
            else:
                # Apply automatic migration based on type
                migrated_data = self._apply_migration(migrated_data, migration)
        
        return True, f"Migrated from {from_version} to {to_version}", migrated_data
    
    def _apply_migration(
        self,
        data: Dict[str, Any],
        migration: Migration
    ) -> Dict[str, Any]:
        """
        Apply a migration to data.
        
        Args:
            data: Data to migrate
            migration: Migration to apply
            
        Returns:
            Migrated data
        """
        result = data.copy()
        
        if migration.migration_type == MigrationType.ADD_FIELD:
            if migration.field_name and migration.new_value is not None:
                result[migration.field_name] = migration.new_value
        
        elif migration.migration_type == MigrationType.REMOVE_FIELD:
            if migration.field_name in result:
                del result[migration.field_name]
        
        elif migration.migration_type == MigrationType.RENAME_FIELD:
            if migration.field_name and migration.new_value:
                if migration.field_name in result:
                    result[migration.new_value] = result[migration.field_name]
                    del result[migration.field_name]
        
        elif migration.migration_type == MigrationType.CHANGE_TYPE:
            if migration.field_name in result and migration.new_value is not None:
                result[migration.field_name] = migration.new_value
        
        elif migration.migration_type == MigrationType.CHANGE_DEFAULT:
            if migration.field_name in result and result[migration.field_name] is None:
                if migration.new_value is not None:
                    result[migration.field_name] = migration.new_value
        
        return result
    
    def get_version_history(
        self,
        version: Optional[str] = None
    ) -> List[SchemaVersion]:
        """
        Get version history.
        
        Args:
            version: Optional specific version to get history for
            
        Returns:
            List of SchemaVersion objects
        """
        if version:
            return [self.versions[version]] if version in self.versions else []
        
        # Return all versions sorted by version number
        sorted_versions = sorted(
            self.versions.values(),
            key=lambda v: [int(x) for x in v.version.split(".")]
        )
        
        return sorted_versions
    
    def compare_versions(
        self,
        version1: str,
        version2: str
    ) -> int:
        """
        Compare two version strings.
        
        Args:
            version1: First version
            version2: Second version
            
        Returns:
            -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        v1_parts = [int(x) for x in version1.split(".")]
        v2_parts = [int(x) for x in version2.split(".")]
        
        # Pad with zeros to match length
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        for v1, v2 in zip(v1_parts, v2_parts):
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
        
        return 0


def create_version_manager(
    repo_root: Path,
    schema_dir: Optional[Path] = None
) -> SchemaVersionManager:
    """Create a schema version manager instance."""
    return SchemaVersionManager(repo_root, schema_dir)