#!/usr/bin/env python3
"""
Pipeline Version Manager
Handles pipeline versioning, migrations, and updates with rollback support.
"""

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Any
from copy import deepcopy
import hashlib


class PipelineVersionManager:
    """Manages pipeline versions and updates."""
    
    def __init__(self, pipeline_name: str, skill_dir: Path):
        self.pipeline_name = pipeline_name
        self.skill_dir = skill_dir
        self.versions_dir = skill_dir / 'versions'
        self.backups_dir = skill_dir / 'backups'
        self.config_file = skill_dir / 'config.json'
        
        self.current_version = self.load_current_version()
        self.available_versions = self.load_available_versions()
        self.migrations = self.load_migrations()
    
    def load_current_version(self) -> str:
        """Load current pipeline version from config."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    return config.get('version', '1.0.0')
            except (json.JSONDecodeError, IOError):
                pass
        return '1.0.0'
    
    def load_available_versions(self) -> List[str]:
        """Load all available pipeline versions."""
        versions = []
        if self.versions_dir.exists():
            for version_dir in self.versions_dir.iterdir():
                if version_dir.is_dir():
                    versions.append(version_dir.name)
        return sorted(versions, key=self._parse_version)
    
    def load_migrations(self) -> Dict[str, Dict[str, Callable]]:
        """Load migration scripts."""
        migrations = {}
        
        if not self.versions_dir.exists():
            return migrations
        
        for version_dir in self.versions_dir.iterdir():
            if not version_dir.is_dir():
                continue
            
            migrations_dir = version_dir / 'migrations'
            if not migrations_dir.exists():
                continue
            
            version = version_dir.name
            if version not in migrations:
                migrations[version] = {}
            
            for migration_file in migrations_dir.glob('from_*.py'):
                from_version = migration_file.stem.replace('from_', '')
                migrations[version][from_version] = self._load_migration(migration_file)
        
        return migrations
    
    def _load_migration(self, migration_file: Path) -> Callable:
        """Load a migration function from a file."""
        spec = {}
        with open(migration_file, 'r') as f:
            exec(f.read(), spec)
        
        if 'migrate' in spec:
            return spec['migrate']
        elif 'migrate_state' in spec:
            return spec['migrate_state']
        else:
            raise ValueError(f"No migration function found in {migration_file}")
    
    def _parse_version(self, version_str: str) -> Tuple[int, int, int]:
        """Parse semantic version string."""
        parts = version_str.split('.')
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare two versions. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
        v1_parts = self._parse_version(v1)
        v2_parts = self._parse_version(v2)
        
        if v1_parts < v2_parts:
            return -1
        elif v1_parts > v2_parts:
            return 1
        else:
            return 0
    
    def check_updates(self) -> Tuple[bool, Optional[str]]:
        """Check if updates are available."""
        if not self.available_versions:
            return False, None
        
        latest = max(self.available_versions, key=self._parse_version)
        if self._compare_versions(latest, self.current_version) > 0:
            return True, latest
        return False, None
    
    def get_migration_path(self, target_version: str) -> List[str]:
        """Get the path of versions to migrate through."""
        if self._compare_versions(target_version, self.current_version) <= 0:
            raise ValueError(f"Target version {target_version} is not newer than current {self.current_version}")
        
        path = []
        current = self.current_version
        
        while self._compare_versions(current, target_version) < 0:
            # Find next version
            next_versions = [
                v for v in self.available_versions
                if self._compare_versions(v, current) > 0
            ]
            
            if not next_versions:
                raise ValueError(f"No migration path from {current} to {target_version}")
            
            # Get the closest next version
            next_version = min(next_versions, key=lambda v: self._parse_version(v))
            path.append(next_version)
            current = next_version
        
        return path
    
    def get_rollback_path(self, target_version: str) -> List[str]:
        """Get the path of versions to rollback through."""
        if self._compare_versions(target_version, self.current_version) >= 0:
            raise ValueError(f"Target version {target_version} is not older than current {self.current_version}")
        
        path = []
        current = self.current_version
        
        while self._compare_versions(current, target_version) > 0:
            # Find previous version
            prev_versions = [
                v for v in self.available_versions
                if self._compare_versions(v, current) < 0
            ]
            
            if not prev_versions:
                raise ValueError(f"No rollback path from {current} to {target_version}")
            
            # Get the closest previous version
            prev_version = max(prev_versions, key=lambda v: self._parse_version(v))
            path.append(prev_version)
            current = prev_version
        
        return path


class MigrationExecutor:
    """Executes state migrations with rollback support."""
    
    def __init__(self, state: Dict, version_manager: PipelineVersionManager):
        self.state = deepcopy(state)
        self.version_manager = version_manager
        self.backup: Optional[Dict] = None
    
    def create_backup(self) -> str:
        """Create a backup of the current state."""
        self.backup = deepcopy(self.state)
        backup_id = self._generate_backup_id()
        return backup_id
    
    def _generate_backup_id(self) -> str:
        """Generate a unique backup ID."""
        timestamp = datetime.now().isoformat()
        state_hash = hashlib.md5(json.dumps(self.state, sort_keys=True).encode()).hexdigest()[:8]
        return f"{timestamp}_{state_hash}"
    
    def apply_migration(self, from_version: str, to_version: str) -> Tuple[bool, str]:
        """Apply a migration from one version to another."""
        if not self.backup:
            self.create_backup()
        
        # Get migration function
        migrations = self.version_manager.migrations
        if to_version not in migrations or from_version not in migrations[to_version]:
            return False, f"No migration found from {from_version} to {to_version}"
        
        migration_func = migrations[to_version][from_version]
        
        try:
            # Apply migration
            self.state = migration_func(self.state)
            
            # Update version in state
            if 'version' in self.state:
                self.state['version'] = to_version
            
            # Validate new state
            self.validate_state(to_version)
            
            return True, f"Successfully migrated from {from_version} to {to_version}"
        except Exception as e:
            # Restore from backup
            self.state = deepcopy(self.backup)
            return False, f"Migration failed: {str(e)}"
    
    def validate_state(self, schema_version: str) -> bool:
        """Validate state against schema version."""
        # Load schema
        schema = self._load_schema(schema_version)
        
        # Validate required fields
        if 'required' in schema:
            for field in schema['required']:
                if field not in self.state:
                    raise ValueError(f"Missing required field: {field}")
        
        # Validate field types
        if 'fields' in schema:
            for field, field_type in schema['fields'].items():
                if field in self.state:
                    if not isinstance(self.state[field], field_type):
                        raise ValueError(f"Field {field} should be {field_type}, got {type(self.state[field])}")
        
        return True
    
    def _load_schema(self, version: str) -> Dict:
        """Load schema for a specific version."""
        schema_file = self.version_manager.versions_dir / version / 'schema.json'
        if schema_file.exists():
            with open(schema_file, 'r') as f:
                return json.load(f)
        return {}
    
    def rollback(self) -> bool:
        """Rollback to backup state."""
        if self.backup:
            self.state = deepcopy(self.backup)
            return True
        return False


class StateValidator:
    """Validates workflow state integrity."""
    
    def __init__(self, schema_dir: Optional[Path] = None):
        self.schema_dir = schema_dir
    
    def validate(self, state: Dict, schema_version: str) -> Tuple[bool, List[str]]:
        """Validate state against schema version."""
        errors = []
        
        # Load schema
        schema = self._load_schema(schema_version)
        
        if not schema:
            errors.append(f"No schema found for version {schema_version}")
            return False, errors
        
        # Validate required fields
        if 'required' in schema:
            for field in schema['required']:
                if field not in state:
                    errors.append(f"Missing required field: {field}")
        
        # Validate field types
        if 'fields' in schema:
            for field, field_config in schema['fields'].items():
                if field in state:
                    expected_type = field_config.get('type')
                    if expected_type:
                        if not self._check_type(state[field], expected_type):
                            errors.append(f"Field {field} should be {expected_type}, got {type(state[field]).__name__}")
                    
                    # Validate enum values
                    if 'enum' in field_config and field in state:
                        if state[field] not in field_config['enum']:
                            errors.append(f"Field {field} has invalid value: {state[field]}")
        
        # Validate nested structures
        if 'nested' in schema:
            for nested_field, nested_schema in schema['nested'].items():
                if nested_field in state and isinstance(state[nested_field], dict):
                    nested_valid, nested_errors = self.validate(state[nested_field], nested_schema)
                    errors.extend([f"{nested_field}.{err}" for err in nested_errors])
        
        return len(errors) == 0, errors
    
    def _load_schema(self, version: str) -> Dict:
        """Load schema for a specific version."""
        if self.schema_dir:
            schema_file = self.schema_dir / version / 'schema.json'
            if schema_file.exists():
                with open(schema_file, 'r') as f:
                    return json.load(f)
        return {}
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            'string': str,
            'integer': int,
            'float': float,
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        python_type = type_map.get(expected_type)
        if python_type:
            return isinstance(value, python_type)
        return True


class BackupManager:
    """Manages state backups for rollback."""
    
    def __init__(self, backups_dir: Path):
        self.backups_dir = backups_dir
        self.backups_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, state: Dict, metadata: Optional[Dict] = None) -> str:
        """Create a backup of the state."""
        backup_id = self._generate_backup_id()
        backup_dir = self.backups_dir / backup_id
        backup_dir.mkdir(exist_ok=True)
        
        # Save state
        state_file = backup_dir / 'state.json'
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
        
        # Save metadata
        metadata_file = backup_dir / 'metadata.json'
        metadata_data = {
            'backup_id': backup_id,
            'timestamp': datetime.now().isoformat(),
            'state_version': state.get('version', 'unknown'),
            **(metadata or {})
        }
        with open(metadata_file, 'w') as f:
            json.dump(metadata_data, f, indent=2)
        
        return backup_id
    
    def _generate_backup_id(self) -> str:
        """Generate a unique backup ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"backup_{timestamp}"
    
    def restore_backup(self, backup_id: str) -> Optional[Dict]:
        """Restore state from backup."""
        backup_dir = self.backups_dir / backup_id
        
        if not backup_dir.exists():
            return None
        
        state_file = backup_dir / 'state.json'
        if state_file.exists():
            with open(state_file, 'r') as f:
                return json.load(f)
        
        return None
    
    def list_backups(self) -> List[Dict]:
        """List all available backups."""
        backups = []
        
        if not self.backups_dir.exists():
            return backups
        
        for backup_dir in self.backups_dir.iterdir():
            if not backup_dir.is_dir():
                continue
            
            metadata_file = backup_dir / 'metadata.json'
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    backups.append(metadata)
        
        return sorted(backups, key=lambda x: x['timestamp'], reverse=True)
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup."""
        backup_dir = self.backups_dir / backup_id
        
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
            return True
        
        return False
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """Delete old backups, keeping only the most recent."""
        backups = self.list_backups()
        
        if len(backups) <= keep_count:
            return 0
        
        to_delete = backups[keep_count:]
        deleted_count = 0
        
        for backup in to_delete:
            if self.delete_backup(backup['backup_id']):
                deleted_count += 1
        
        return deleted_count


class PipelineUpdateManager:
    """High-level manager for pipeline updates."""
    
    def __init__(self, pipeline_name: str, skill_dir: Path):
        self.pipeline_name = pipeline_name
        self.skill_dir = skill_dir
        self.version_manager = PipelineVersionManager(pipeline_name, skill_dir)
        self.backup_manager = BackupManager(skill_dir / 'backups')
        self.validator = StateValidator(skill_dir / 'versions')
    
    def check_for_updates(self) -> Tuple[bool, Optional[str]]:
        """Check if updates are available."""
        return self.version_manager.check_updates()
    
    def update_to_version(self, target_version: str, state: Dict, dry_run: bool = False) -> Tuple[bool, str]:
        """Update pipeline to target version."""
        # Check if update is needed
        if self.version_manager._compare_versions(target_version, self.version_manager.current_version) <= 0:
            return False, f"Already at version {target_version} or newer"
        
        # Get migration path
        try:
            migration_path = self.version_manager.get_migration_path(target_version)
        except ValueError as e:
            return False, str(e)
        
        if dry_run:
            return True, f"Would migrate through: {' -> '.join(migration_path)}"
        
        # Create backup
        backup_id = self.backup_manager.create_backup(state, {
            'pipeline': self.pipeline_name,
            'from_version': self.version_manager.current_version,
            'to_version': target_version
        })
        
        # Execute migrations
        executor = MigrationExecutor(state, self.version_manager)
        current_version = self.version_manager.current_version
        
        for next_version in migration_path:
            success, message = executor.apply_migration(current_version, next_version)
            if not success:
                return False, f"Migration failed: {message}\nBackup available: {backup_id}"
            current_version = next_version
        
        # Update config version
        self._update_config_version(target_version)
        
        return True, f"Successfully updated to version {target_version}\nBackup: {backup_id}"
    
    def rollback_to_version(self, target_version: str, state: Dict, backup_id: Optional[str] = None) -> Tuple[bool, str]:
        """Rollback pipeline to target version."""
        # If backup_id provided, restore from backup
        if backup_id:
            restored_state = self.backup_manager.restore_backup(backup_id)
            if restored_state:
                state.clear()
                state.update(restored_state)
                self._update_config_version(state.get('version', '1.0.0'))
                return True, f"Restored from backup {backup_id}"
            else:
                return False, f"Backup {backup_id} not found"
        
        # Otherwise, rollback through versions
        try:
            rollback_path = self.version_manager.get_rollback_path(target_version)
        except ValueError as e:
            return False, str(e)
        
        # Create backup before rollback
        backup_id = self.backup_manager.create_backup(state, {
            'pipeline': self.pipeline_name,
            'from_version': self.version_manager.current_version,
            'to_version': target_version,
            'operation': 'rollback'
        })
        
        # Rollback (simplified - would need rollback migrations)
        self._update_config_version(target_version)
        
        return True, f"Rolled back to version {target_version}\nBackup: {backup_id}"
    
    def _update_config_version(self, version: str):
        """Update version in config file."""
        config_file = self.skill_dir / 'config.json'
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        config['version'] = version
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def list_versions(self) -> List[str]:
        """List all available versions."""
        return self.version_manager.available_versions
    
    def get_current_version(self) -> str:
        """Get current pipeline version."""
        return self.version_manager.current_version
