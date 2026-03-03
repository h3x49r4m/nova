"""Cache Manager - Provides caching for expensive operations.

This module provides a flexible caching system for expensive operations,
including in-memory, file-based, and persistent caching strategies.
"""

import hashlib
import json
import pickle
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .exceptions import IFlowError, ErrorCode


class CacheStrategy(Enum):
    """Cache eviction strategies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live


class CacheBackend(Enum):
    """Cache backend types."""
    MEMORY = "memory"
    FILE = "file"
    PERSISTENT = "persistent"


@dataclass
class CacheEntry:
    """Represents a cache entry."""
    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[float] = None  # Time to live in seconds
    size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self):
        """Update last accessed time and access count."""
        self.last_accessed = time.time()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    hit_rate: float = 0.0
    
    def calculate_hit_rate(self):
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total > 0:
            self.hit_rate = (self.hits / total) * 100
        else:
            self.hit_rate = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        self.calculate_hit_rate()
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size_bytes": self.size_bytes,
            "entry_count": self.entry_count,
            "hit_rate": f"{self.hit_rate:.2f}%"
        }


class CacheBackendProvider(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache."""
        pass
    
    @abstractmethod
    def set(self, entry: CacheEntry):
        """Set entry in cache."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        pass
    
    @abstractmethod
    def clear(self):
        """Clear all entries."""
        pass
    
    @abstractmethod
    def keys(self) -> List[str]:
        """Get all keys."""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """Get cache size in bytes."""
        pass


class MemoryCacheBackend(CacheBackendProvider):
    """In-memory cache backend."""
    
    def __init__(self, max_size_mb: int = 100):
        """
        Initialize memory cache.
        
        Args:
            max_size_mb: Maximum cache size in MB
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache."""
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                entry.touch()
            return entry
    
    def set(self, entry: CacheEntry):
        """Set entry in cache."""
        with self._lock:
            self._cache[entry.key] = entry
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self):
        """Clear all entries."""
        with self._lock:
            self._cache.clear()
    
    def keys(self) -> List[str]:
        """Get all keys."""
        with self._lock:
            return list(self._cache.keys())
    
    def size(self) -> int:
        """Get cache size in bytes."""
        with self._lock:
            return sum(entry.size for entry in self._cache.values())


class FileCacheBackend(CacheBackendProvider):
    """File-based cache backend."""
    
    def __init__(self, cache_dir: Path, max_size_mb: int = 500):
        """
        Initialize file cache.
        
        Args:
            cache_dir: Cache directory
            max_size_mb: Maximum cache size in MB
        """
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._lock = threading.RLock()
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for key."""
        # Use hash to create safe filename
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.cache"
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get entry from cache."""
        with self._lock:
            file_path = self._get_file_path(key)
            
            if not file_path.exists():
                return None
            
            try:
                with open(file_path, 'rb') as f:
                    entry = pickle.load(f)
                
                entry.touch()
                
                # Update file
                self._save_entry(entry)
                
                return entry
            
            except Exception:
                # Corrupted file, delete it
                file_path.unlink(missing_ok=True)
                return None
    
    def set(self, entry: CacheEntry):
        """Set entry in cache."""
        with self._lock:
            self._save_entry(entry)
    
    def _save_entry(self, entry: CacheEntry):
        """Save entry to file."""
        file_path = self._get_file_path(entry.key)
        
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(entry, f)
        except Exception:
            pass
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            file_path = self._get_file_path(key)
            
            if file_path.exists():
                file_path.unlink()
                return True
            
            return False
    
    def clear(self):
        """Clear all entries."""
        with self._lock:
            for file_path in self.cache_dir.glob("*.cache"):
                file_path.unlink(missing_ok=True)
    
    def keys(self) -> List[str]:
        """Get all keys."""
        with self._lock:
            keys = []
            for file_path in self.cache_dir.glob("*.cache"):
                try:
                    with open(file_path, 'rb') as f:
                        entry = pickle.load(f)
                    keys.append(entry.key)
                except Exception:
                    file_path.unlink(missing_ok=True)
            return keys
    
    def size(self) -> int:
        """Get cache size in bytes."""
        with self._lock:
            total = 0
            for file_path in self.cache_dir.glob("*.cache"):
                total += file_path.stat().st_size
            return total


class PersistentCacheBackend(FileCacheBackend):
    """Persistent cache backend with metadata."""
    
    def __init__(self, cache_dir: Path, max_size_mb: int = 500):
        """
        Initialize persistent cache.
        
        Args:
            cache_dir: Cache directory
            max_size_mb: Maximum cache size in MB
        """
        super().__init__(cache_dir, max_size_mb)
        self.metadata_file = cache_dir / "metadata.json"
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    self.metadata = json.load(f)
            except Exception:
                self.metadata = {}
        else:
            self.metadata = {}
    
    def _save_metadata(self):
        """Save metadata to file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception:
            pass


class CacheManager:
    """Manages caching for expensive operations."""
    
    def __init__(
        self,
        backend: CacheBackend = CacheBackend.MEMORY,
        cache_dir: Optional[Path] = None,
        max_size_mb: int = 100,
        strategy: CacheStrategy = CacheStrategy.LRU,
        default_ttl: Optional[int] = None
    ):
        """
        Initialize cache manager.
        
        Args:
            backend: Cache backend type
            cache_dir: Cache directory for file-based backends
            max_size_mb: Maximum cache size in MB
            strategy: Eviction strategy
            default_ttl: Default TTL in seconds
        """
        self.backend_type = backend
        self.strategy = strategy
        self.default_ttl = default_ttl
        
        # Initialize backend
        if backend == CacheBackend.MEMORY:
            self.backend = MemoryCacheBackend(max_size_mb)
        elif backend == CacheBackend.FILE:
            cache_dir = cache_dir or Path(".cache")
            self.backend = FileCacheBackend(cache_dir, max_size_mb)
        elif backend == CacheBackend.PERSISTENT:
            cache_dir = cache_dir or Path(".cache")
            self.backend = PersistentCacheBackend(cache_dir, max_size_mb)
        else:
            raise IFlowError(
                f"Unknown cache backend: {backend}",
                ErrorCode.INVALID_ARGUMENT
            )
        
        self.stats = CacheStats()
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        entry = self.backend.get(key)
        
        if entry is None:
            with self._lock:
                self.stats.misses += 1
            return None
        
        if entry.is_expired():
            self.delete(key)
            with self._lock:
                self.stats.misses += 1
            return None
        
        with self._lock:
            self.stats.hits += 1
        
        return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            metadata: Optional metadata
        """
        # Calculate size
        try:
            size = len(pickle.dumps(value))
        except Exception:
            size = len(str(value))
        
        entry = CacheEntry(
            key=key,
            value=value,
            ttl=ttl or self.default_ttl,
            size=size,
            metadata=metadata or {}
        )
        
        # Check if eviction needed
        self._check_eviction()
        
        self.backend.set(entry)
        
        with self._lock:
            self.stats.entry_count = len(self.backend.keys())
            self.stats.size_bytes = self.backend.size()
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted
        """
        deleted = self.backend.delete(key)
        
        with self._lock:
            self.stats.entry_count = len(self.backend.keys())
            self.stats.size_bytes = self.backend.size()
        
        return deleted
    
    def clear(self):
        """Clear all cached values."""
        self.backend.clear()
        
        with self._lock:
            self.stats.entry_count = 0
            self.stats.size_bytes = 0
    
    def keys(self) -> List[str]:
        """Get all cache keys."""
        return self.backend.keys()
    
    def size(self) -> int:
        """Get cache size in bytes."""
        return self.backend.size()
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            self.stats.entry_count = len(self.backend.keys())
            self.stats.size_bytes = self.backend.size()
            return self.stats
    
    def _check_eviction(self):
        """Check if eviction is needed and perform it."""
        if self.strategy == CacheStrategy.TTL:
            return  # TTL is handled by is_expired()
        
        # Check if over size limit
        current_size = self.backend.size()
        
        # Convert backend max_size to bytes
        if isinstance(self.backend, MemoryCacheBackend):
            max_size = self.backend.max_size_bytes
        elif isinstance(self.backend, FileCacheBackend):
            max_size = self.backend.max_size_bytes
        else:
            return
        
        if current_size <= max_size:
            return
        
        # Evict entries
        self._evict_entries(max_size)
    
    def _evict_entries(self, target_size: int):
        """Evict entries based on strategy."""
        keys = self.backend.keys()
        
        if not keys:
            return
        
        if self.strategy == CacheStrategy.LRU:
            # Evict least recently used
            entries = [(k, self.backend.get(k)) for k in keys]
            entries.sort(key=lambda x: x[1].last_accessed if x[1] else 0)
        
        elif self.strategy == CacheStrategy.LFU:
            # Evict least frequently used
            entries = [(k, self.backend.get(k)) for k in keys]
            entries.sort(key=lambda x: x[1].access_count if x[1] else 0)
        
        elif self.strategy == CacheStrategy.FIFO:
            # Evict oldest
            entries = [(k, self.backend.get(k)) for k in keys]
            entries.sort(key=lambda x: x[1].created_at if x[1] else 0)
        
        else:
            return
        
        # Evict until under target size
        current_size = self.backend.size()
        
        for key, entry in entries:
            if current_size <= target_size:
                break
            
            if entry:
                current_size -= entry.size
                self.delete(key)
                
                with self._lock:
                    self.stats.evictions += 1
    
    def cached(
        self,
        ttl: Optional[int] = None,
        key_prefix: str = ""
    ):
        """
        Decorator for caching function results.
        
        Args:
            ttl: Time to live in seconds
            key_prefix: Prefix for cache key
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                # Generate cache key
                key = self._generate_key(func, args, kwargs, key_prefix)
                
                # Try to get from cache
                result = self.get(key)
                if result is not None:
                    return result
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Cache result
                self.set(key, result, ttl)
                
                return result
            
            return wrapper
        return decorator
    
    def _generate_key(
        self,
        func: Callable,
        args: Tuple,
        kwargs: Dict[str, Any],
        prefix: str
    ) -> str:
        """
        Generate cache key for function call.
        
        Args:
            func: Function being called
            args: Positional arguments
            kwargs: Keyword arguments
            prefix: Key prefix
            
        Returns:
            Cache key
        """
        # Create key components
        key_parts = [prefix, func.__name__]
        
        # Add args
        for arg in args:
            key_parts.append(str(arg))
        
        # Add kwargs (sorted for consistency)
        for k in sorted(kwargs.keys()):
            key_parts.append(f"{k}={kwargs[k]}")
        
        # Create key string
        key_str = ":".join(key_parts)
        
        # Hash if too long
        if len(key_str) > 200:
            key_str = hashlib.md5(key_str.encode()).hexdigest()
        
        return key_str
    
    def invalidate_prefix(self, prefix: str):
        """
        Invalidate all keys with given prefix.
        
        Args:
            prefix: Key prefix to invalidate
        """
        keys = self.backend.keys()
        
        for key in keys:
            if key.startswith(prefix):
                self.delete(key)
    
    def invalidate_pattern(self, pattern: str):
        """
        Invalidate keys matching pattern.
        
        Args:
            pattern: Pattern to match (supports * wildcard)
        """
        import fnmatch
        
        keys = self.backend.keys()
        
        for key in keys:
            if fnmatch.fnmatch(key, pattern):
                self.delete(key)


def create_cache_manager(
    backend: CacheBackend = CacheBackend.MEMORY,
    cache_dir: Optional[Path] = None,
    max_size_mb: int = 100,
    strategy: CacheStrategy = CacheStrategy.LRU,
    default_ttl: Optional[int] = None
) -> CacheManager:
    """Create a cache manager instance."""
    return CacheManager(backend, cache_dir, max_size_mb, strategy, default_ttl)


# Global cache instance
_global_cache: Optional[CacheManager] = None


def get_global_cache() -> CacheManager:
    """Get or create global cache instance."""
    global _global_cache
    
    if _global_cache is None:
        _global_cache = create_cache_manager()
    
    return _global_cache


def clear_global_cache():
    """Clear global cache instance."""
    global _global_cache
    if _global_cache is not None:
        _global_cache.clear()


def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    cache_manager: Optional[CacheManager] = None
):
    """
    Decorator for caching function results using global cache.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        cache_manager: Optional cache manager instance
        
    Returns:
        Decorator function
    """
    if cache_manager is None:
        cache_manager = get_global_cache()
    
    return cache_manager.cached(ttl, key_prefix)