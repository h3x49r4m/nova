"""State Versioning - Tracks and manages state file versions over time.

This module provides versioning capabilities for state files, allowing
tracking of changes, rollback to previous versions, and version history.
"""

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import IFlowError, ErrorCode


@dataclass
class StateVersion:
    """Represents a version of a state file."""
    version_id: str
    file_path: str
    timestamp: str
    author: str = "system"
    description: str = ""
    parent_version_id: Optional[str] = None
    checksum: str = ""
    size_bytes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert version to dictionary."""
        return {
            "version_id": self.version_id,
            "file_path": self.file_path,
            "timestamp": self.timestamp,
            "author": self.author,
            "description": self.description,
            "parent_version_id": self.parent_version_id,
            "checksum": self.checksum,
            "size_bytes": self.size_bytes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateVersion":
        """Create version from dictionary."""
        return cls(
            version_id=data["version_id"],
            file_path=data["file_path"],
            timestamp=data["timestamp"],
            author=data.get("author", "system"),
            description=data.get("description", ""),
            parent_version_id=data.get("parent_version_id"),
            checksum=data.get("checksum", ""),
            size_bytes=data.get("size_bytes", 0)
        )


@dataclass
class VersionHistory:
    """Version history for a specific file."""
    file_path: str
    versions: List[StateVersion] = field(default_factory=list)
    current_version_id: Optional[str] = None
    
    def add_version(self, version: StateVersion) -> None:
        """Add a version to the history."""
        self.versions.append(version)
        self.current_version_id = version.version_id
    
    def get_version(self, version_id: str) -> Optional[StateVersion]:
        """Get a specific version by ID."""
        for version in self.versions:
            if version.version_id == version_id:
                return version
        return None
    
    def get_latest_version(self) -> Optional[StateVersion]:
        """Get the latest version."""
        return self.versions[-1] if self.versions else None
    
    def get_version_chain(self, version_id: str) -> List[StateVersion]:
        """Get the chain of versions leading to this version."""
        chain = []
        current = self.get_version(version_id)
        while current:
            chain.insert(0, current)
            if current.parent_version_id:
                current = self.get_version(current.parent_version_id)
            else:
                break
        return chain
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert history to dictionary."""
        return {
            "file_path": self.file_path,
            "versions": [v.to_dict() for v in self.versions],
            "current_version_id": self.current_version_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VersionHistory":
        """Create history from dictionary."""
        return cls(
            file_path=data["file_path"],
            versions=[StateVersion.from_dict(v) for v in data.get("versions", [])],
            current_version_id=data.get("current_version_id")
        )


class StateVersionManager:
    """Manages state file versioning."""
    
    def __init__(self, state_dir: Path, max_versions: int = 100):
        """
        Initialize state version manager.
        
        Args:
            state_dir: Directory containing state files
            max_versions: Maximum number of versions to keep per file
        """
        self.state_dir = state_dir
        self.max_versions = max_versions
        self.versions_dir = state_dir / ".versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.version_index_file = self.versions_dir / "version_index.json"
        
        self.version_histories: Dict[str, VersionHistory] = {}
        self._load_version_index()
    
    def _load_version_index(self) -> None:
        """Load version index from file."""
        if self.version_index_file.exists():
            try:
                with open(self.version_index_file, 'r') as f:
                    index_data = json.load(f)
                    for file_path, history_data in index_data.items():
                        self.version_histories[file_path] = VersionHistory.from_dict(history_data)
            except (json.JSONDecodeError, IOError):
                self.version_histories = {}
    
    def _save_version_index(self) -> None:
        """Save version index to file."""
        try:
            index_data = {
                file_path: history.to_dict()
                for file_path, history in self.version_histories.items()
            }
            with open(self.version_index_file, 'w') as f:
                json.dump(index_data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save version index: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate checksum of a file."""
        import hashlib
        hash_obj = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except IOError:
            return ""
    
    def _get_version_dir(self, file_path: Path, version_id: str) -> Path:
        """Get the directory for a specific version."""
        # Create a safe directory name from file path
        safe_name = str(file_path).replace('/', '_').replace('\\', '_')
        return self.versions_dir / safe_name / version_id
    
    def create_version(
        self,
        file_path: Path,
        author: str = "system",
        description: str = ""
    ) -> StateVersion:
        """
        Create a new version of a state file.
        
        Args:
            file_path: Path to the state file
            author: Author of the change
            description: Description of the change
            
        Returns:
            Created version
            
        Raises:
            IFlowError if file doesn't exist
        """
        import uuid
        
        if not file_path.exists():
            raise IFlowError(
                f"Cannot version non-existent file: {file_path}",
                ErrorCode.FILE_NOT_FOUND
            )
        
        # Get relative path from state dir
        rel_path = str(file_path.relative_to(self.state_dir))
        
        # Get current version for parent reference
        history = self.version_histories.get(rel_path)
        parent_version_id = history.current_version_id if history else None
        
        # Create version ID
        version_id = str(uuid.uuid4())
        
        # Calculate checksum and size
        checksum = self._calculate_checksum(file_path)
        size_bytes = file_path.stat().st_size
        
        # Create version object
        version = StateVersion(
            version_id=version_id,
            file_path=rel_path,
            timestamp=datetime.now().isoformat(),
            author=author,
            description=description,
            parent_version_id=parent_version_id,
            checksum=checksum,
            size_bytes=size_bytes
        )
        
        # Copy file to version storage
        version_dir = self._get_version_dir(file_path, version_id)
        version_dir.mkdir(parents=True, exist_ok=True)
        version_file = version_dir / file_path.name
        shutil.copy2(file_path, version_file)
        
        # Update or create history
        if not history:
            history = VersionHistory(file_path=rel_path)
            self.version_histories[rel_path] = history
        
        history.add_version(version)
        
        # Prune old versions if needed
        self._prune_old_versions(history)
        
        # Save index
        self._save_version_index()
        
        return version
    
    def restore_version(
        self,
        file_path: Path,
        version_id: str
    ) -> None:
        """
        Restore a file to a specific version.
        
        Args:
            file_path: Path to the state file
            version_id: Version ID to restore
            
        Raises:
            IFlowError if version not found
        """
        # Get relative path
        rel_path = str(file_path.relative_to(self.state_dir))
        
        # Get history
        history = self.version_histories.get(rel_path)
        if not history:
            raise IFlowError(
                f"No version history found for: {rel_path}",
                ErrorCode.FILE_NOT_FOUND
            )
        
        # Get version
        version = history.get_version(version_id)
        if not version:
            raise IFlowError(
                f"Version {version_id} not found for: {rel_path}",
                ErrorCode.FILE_NOT_FOUND
            )
        
        # Get version file
        version_dir = self._get_version_dir(file_path, version_id)
        version_file = version_dir / file_path.name
        
        if not version_file.exists():
            raise IFlowError(
                f"Version file not found: {version_file}",
                ErrorCode.FILE_NOT_FOUND
            )
        
        # Restore file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(version_file, file_path)
        
        # Update current version in history
        # Note: We create a new version pointing to the restored version
        # This maintains the chain
        new_version = self.create_version(
            file_path,
            author="system",
            description=f"Restored from version {version_id}"
        )
        # Update parent to point to the restored version
        new_version.parent_version_id = version_id
        self._save_version_index()
    
    def get_version_history(
        self,
        file_path: Path,
        limit: int = 50
    ) -> List[StateVersion]:
        """
        Get version history for a file.
        
        Args:
            file_path: Path to the state file
            limit: Maximum number of versions to return
            
        Returns:
            List of versions
        """
        rel_path = str(file_path.relative_to(self.state_dir))
        history = self.version_histories.get(rel_path)
        
        if not history:
            return []
        
        return history.versions[-limit:]
    
    def get_version(
        self,
        file_path: Path,
        version_id: str
    ) -> Optional[StateVersion]:
        """
        Get a specific version of a file.
        
        Args:
            file_path: Path to the state file
            version_id: Version ID
            
        Returns:
            Version or None if not found
        """
        rel_path = str(file_path.relative_to(self.state_dir))
        history = self.version_histories.get(rel_path)
        
        if not history:
            return None
        
        return history.get_version(version_id)
    
    def get_current_version(self, file_path: Path) -> Optional[StateVersion]:
        """
        Get the current version of a file.
        
        Args:
            file_path: Path to the state file
            
        Returns:
            Current version or None if no versions
        """
        rel_path = str(file_path.relative_to(self.state_dir))
        history = self.version_histories.get(rel_path)
        
        if not history:
            return None
        
        return history.get_latest_version()
    
    def compare_versions(
        self,
        file_path: Path,
        version_id1: str,
        version_id2: str
    ) -> Dict[str, Any]:
        """
        Compare two versions of a file.
        
        Args:
            file_path: Path to the state file
            version_id1: First version ID
            version_id2: Second version ID
            
        Returns:
            Comparison result
        """
        rel_path = str(file_path.relative_to(self.state_dir))
        history = self.version_histories.get(rel_path)
        
        if not history:
            return {"error": "No version history found"}
        
        version1 = history.get_version(version_id1)
        version2 = history.get_version(version_id2)
        
        if not version1 or not version2:
            return {"error": "One or both versions not found"}
        
        # Load version data
        version_file1 = self._get_version_dir(file_path, version_id1) / file_path.name
        version_file2 = self._get_version_dir(file_path, version_id2) / file_path.name
        
        data1 = {}
        data2 = {}
        
        if version_file1.exists():
            try:
                with open(version_file1, 'r') as f:
                    data1 = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        if version_file2.exists():
            try:
                with open(version_file2, 'r') as f:
                    data2 = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        return {
            "version1": version1.to_dict(),
            "version2": version2.to_dict(),
            "data_changed": data1 != data2,
            "checksum_changed": version1.checksum != version2.checksum,
            "size_diff": version2.size_bytes - version1.size_bytes
        }
    
    def delete_version(
        self,
        file_path: Path,
        version_id: str
    ) -> None:
        """
        Delete a specific version.
        
        Args:
            file_path: Path to the state file
            version_id: Version ID to delete
            
        Raises:
            IFlowError if version is current or not found
        """
        rel_path = str(file_path.relative_to(self.state_dir))
        history = self.version_histories.get(rel_path)
        
        if not history:
            raise IFlowError(
                f"No version history found for: {rel_path}",
                ErrorCode.FILE_NOT_FOUND
            )
        
        # Find the version
        version = history.get_version(version_id)
        if not version:
            raise IFlowError(
                f"Version {version_id} not found for: {rel_path}",
                ErrorCode.FILE_NOT_FOUND
            )
        
        # Check if it's the current version
        if history.current_version_id == version_id:
            raise IFlowError(
                "Cannot delete the current version",
                ErrorCode.VALIDATION_FAILED
            )
        
        # Remove version from history
        history.versions = [
            v for v in history.versions if v.version_id != version_id
        ]
        
        # Delete version file
        version_dir = self._get_version_dir(file_path, version_id)
        if version_dir.exists():
            shutil.rmtree(version_dir)
        
        # Save index
        self._save_version_index()
    
    def _prune_old_versions(self, history: VersionHistory) -> None:
        """Prune old versions beyond max_versions."""
        if len(history.versions) > self.max_versions:
            # Keep the most recent versions
            versions_to_remove = history.versions[:-self.max_versions]
            
            for version in versions_to_remove:
                # Remove version file
                file_path = self.state_dir / version.file_path
                version_dir = self._get_version_dir(file_path, version.version_id)
                if version_dir.exists():
                    shutil.rmtree(version_dir)
            
            # Update versions list
            history.versions = history.versions[-self.max_versions:]
    
    def get_all_histories(self) -> Dict[str, VersionHistory]:
        """Get all version histories."""
        return self.version_histories.copy()
    
    def cleanup_unused_versions(self, max_age_days: int = 30) -> int:
        """
        Clean up unused version files.
        
        Args:
            max_age_days: Maximum age in days to keep unused versions
            
        Returns:
            Number of versions cleaned up
        """
        cleaned = 0
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)
        
        for rel_path, history in self.version_histories.items():
            file_path = self.state_dir / rel_path
            
            # Find versions that are old and not current
            for version in history.versions:
                if version.version_id != history.current_version_id:
                    version_timestamp = datetime.fromisoformat(version.timestamp).timestamp()
                    if version_timestamp < cutoff:
                        try:
                            version_dir = self._get_version_dir(file_path, version.version_id)
                            if version_dir.exists():
                                shutil.rmtree(version_dir)
                                cleaned += 1
                        except (IOError, OSError):
                            pass
        
        return cleaned
