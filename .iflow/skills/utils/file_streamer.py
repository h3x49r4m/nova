"""File Streaming Module - Provides efficient streaming for large file operations.

This module implements streaming utilities for handling large files efficiently,
including chunked reading, line-by-line processing, and memory-efficient operations.
"""

import asyncio
import hashlib
from pathlib import Path
from typing import AsyncIterator, Iterator, Optional, Callable, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json


class StreamMode(Enum):
    """Streaming mode for file operations."""
    CHUNK = "chunk"
    LINE = "line"
    JSON = "json"


@dataclass
class StreamConfig:
    """Configuration for file streaming."""
    chunk_size: int = 8192
    max_memory_mb: int = 100
    mode: StreamMode = StreamMode.CHUNK
    encoding: str = 'utf-8'
    errors: str = 'replace'


class FileStreamer:
    """Efficient file streaming for large files."""

    def __init__(self, config: Optional[StreamConfig] = None):
        """
        Initialize file streamer.

        Args:
            config: Streaming configuration
        """
        self.config = config or StreamConfig()

    def stream_chunks(
        self,
        file_path: Path,
        chunk_size: Optional[int] = None
    ) -> Iterator[bytes]:
        """
        Stream file in chunks (synchronous).

        Args:
            file_path: Path to the file
            chunk_size: Size of chunks to read

        Yields:
            File chunks as bytes
        """
        chunk_size = chunk_size or self.config.chunk_size

        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    def stream_lines(
        self,
        file_path: Path,
        encoding: Optional[str] = None,
        errors: Optional[str] = None
    ) -> Iterator[str]:
        """
        Stream file line by line (synchronous).

        Args:
            file_path: Path to the file
            encoding: File encoding
            errors: Error handling strategy

        Yields:
            File lines as strings
        """
        encoding = encoding or self.config.encoding
        errors = errors or self.config.errors

        with open(file_path, 'r', encoding=encoding, errors=errors) as f:
            for line in f:
                yield line.rstrip('\n\r')

    def stream_json_objects(
        self,
        file_path: Path,
        encoding: Optional[str] = None,
        errors: Optional[str] = None
    ) -> Iterator[dict]:
        """
        Stream JSON objects from a file (one per line).

        Args:
            file_path: Path to the file
            encoding: File encoding
            errors: Error handling strategy

        Yields:
            JSON objects as dictionaries
        """
        for line in self.stream_lines(file_path, encoding, errors):
            if line.strip():
                yield json.loads(line)

    async def stream_chunks_async(
        self,
        file_path: Path,
        chunk_size: Optional[int] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream file in chunks (asynchronous).

        Args:
            file_path: Path to the file
            chunk_size: Size of chunks to read

        Yields:
            File chunks as bytes
        """
        chunk_size = chunk_size or self.config.chunk_size
        loop = asyncio.get_event_loop()

        with open(file_path, 'rb') as f:
            while True:
                chunk = await loop.run_in_executor(None, f.read, chunk_size)
                if not chunk:
                    break
                yield chunk

    async def stream_lines_async(
        self,
        file_path: Path,
        encoding: Optional[str] = None,
        errors: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Stream file line by line (asynchronous).

        Args:
            file_path: Path to the file
            encoding: File encoding
            errors: Error handling strategy

        Yields:
            File lines as strings
        """
        encoding = encoding or self.config.encoding
        errors = errors or self.config.errors

        async for chunk in self.stream_chunks_async(file_path):
            text = chunk.decode(encoding, errors=errors)
            for line in text.splitlines(keepends=False):
                yield line

    async def stream_json_objects_async(
        self,
        file_path: Path,
        encoding: Optional[str] = None,
        errors: Optional[str] = None
    ) -> AsyncIterator[dict]:
        """
        Stream JSON objects from a file (asynchronous).

        Args:
            file_path: Path to the file
            encoding: File encoding
            errors: Error handling strategy

        Yields:
            JSON objects as dictionaries
        """
        async for line in self.stream_lines_async(file_path, encoding, errors):
            if line.strip():
                yield json.loads(line)

    def calculate_hash(
        self,
        file_path: Path,
        algorithm: str = 'sha256',
        chunk_size: Optional[int] = None
    ) -> str:
        """
        Calculate file hash with streaming (synchronous).

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use
            chunk_size: Size of chunks to read

        Returns:
            Hexadecimal hash string
        """
        hash_obj = hashlib.new(algorithm)
        chunk_size = chunk_size or self.config.chunk_size

        for chunk in self.stream_chunks(file_path, chunk_size):
            hash_obj.update(chunk)

        return hash_obj.hexdigest()

    async def calculate_hash_async(
        self,
        file_path: Path,
        algorithm: str = 'sha256',
        chunk_size: Optional[int] = None
    ) -> str:
        """
        Calculate file hash with streaming (asynchronous).

        Args:
            file_path: Path to the file
            algorithm: Hash algorithm to use
            chunk_size: Size of chunks to read

        Returns:
            Hexadecimal hash string
        """
        hash_obj = hashlib.new(algorithm)
        chunk_size = chunk_size or self.config.chunk_size

        async for chunk in self.stream_chunks_async(file_path, chunk_size):
            hash_obj.update(chunk)

        return hash_obj.hexdigest()

    def count_lines(
        self,
        file_path: Path,
        encoding: Optional[str] = None,
        errors: Optional[str] = None
    ) -> int:
        """
        Count lines in a file with streaming (synchronous).

        Args:
            file_path: Path to the file
            encoding: File encoding
            errors: Error handling strategy

        Returns:
            Number of lines in the file
        """
        count = 0
        for _ in self.stream_lines(file_path, encoding, errors):
            count += 1
        return count

    async def count_lines_async(
        self,
        file_path: Path,
        encoding: Optional[str] = None,
        errors: Optional[str] = None
    ) -> int:
        """
        Count lines in a file with streaming (asynchronous).

        Args:
            file_path: Path to the file
            encoding: File encoding
            errors: Error handling strategy

        Returns:
            Number of lines in the file
        """
        count = 0
        async for _ in self.stream_lines_async(file_path, encoding, errors):
            count += 1
        return count

    def process_lines(
        self,
        file_path: Path,
        processor: Callable[[str], Any],
        encoding: Optional[str] = None,
        errors: Optional[str] = None
    ) -> list:
        """
        Process each line in a file with a function (synchronous).

        Args:
            file_path: Path to the file
            processor: Function to process each line
            encoding: File encoding
            errors: Error handling strategy

        Returns:
            List of processed results
        """
        results = []
        for line in self.stream_lines(file_path, encoding, errors):
            results.append(processor(line))
        return results

    async def process_lines_async(
        self,
        file_path: Path,
        processor: Callable[[str], Any],
        encoding: Optional[str] = None,
        errors: Optional[str] = None,
        batch_size: int = 100
    ) -> list:
        """
        Process each line in a file with a function (asynchronous).

        Args:
            file_path: Path to the file
            processor: Function to process each line
            encoding: File encoding
            errors: Error handling strategy
            batch_size: Number of lines to process in parallel

        Returns:
            List of processed results
        """
        results = []
        batch = []

        async for line in self.stream_lines_async(file_path, encoding, errors):
            batch.append(line)

            if len(batch) >= batch_size:
                # Process batch in parallel
                batch_results = await asyncio.gather(
                    *[asyncio.to_thread(processor, line) for line in batch]
                )
                results.extend(batch_results)
                batch = []

        # Process remaining lines
        if batch:
            batch_results = await asyncio.gather(
                *[asyncio.to_thread(processor, line) for line in batch]
            )
            results.extend(batch_results)

        return results

    def filter_lines(
        self,
        file_path: Path,
        predicate: Callable[[str], bool],
        encoding: Optional[str] = None,
        errors: Optional[str] = None
    ) -> list:
        """
        Filter lines in a file based on a predicate (synchronous).

        Args:
            file_path: Path to the file
            predicate: Function to test each line
            encoding: File encoding
            errors: Error handling strategy

        Returns:
            List of lines that match the predicate
        """
        return [
            line for line in self.stream_lines(file_path, encoding, errors)
            if predicate(line)
        ]

    async def filter_lines_async(
        self,
        file_path: Path,
        predicate: Callable[[str], bool],
        encoding: Optional[str] = None,
        errors: Optional[str] = None
    ) -> list:
        """
        Filter lines in a file based on a predicate (asynchronous).

        Args:
            file_path: Path to the file
            predicate: Function to test each line
            encoding: File encoding
            errors: Error handling strategy

        Returns:
            List of lines that match the predicate
        """
        results = []
        async for line in self.stream_lines_async(file_path, encoding, errors):
            if predicate(line):
                results.append(line)
        return results

    def get_file_size(self, file_path: Path) -> int:
        """
        Get file size.

        Args:
            file_path: Path to the file

        Returns:
            File size in bytes
        """
        return file_path.stat().st_size

    def is_large_file(
        self,
        file_path: Path,
        threshold_mb: Optional[int] = None
    ) -> bool:
        """
        Check if file is larger than threshold.

        Args:
            file_path: Path to the file
            threshold_mb: Threshold in megabytes

        Returns:
            True if file is larger than threshold
        """
        threshold_mb = threshold_mb or self.config.max_memory_mb
        file_size_mb = self.get_file_size(file_path) / (1024 * 1024)
        return file_size_mb > threshold_mb


# Convenience functions for backward compatibility
def stream_file_chunks(
    file_path: Path,
    chunk_size: int = 8192
) -> Iterator[bytes]:
    """
    Stream file in chunks.

    Args:
        file_path: Path to the file
        chunk_size: Size of chunks to read

    Yields:
        File chunks as bytes
    """
    streamer = FileStreamer()
    yield from streamer.stream_chunks(file_path, chunk_size)


def stream_file_lines(
    file_path: Path,
    encoding: str = 'utf-8',
    errors: str = 'replace'
) -> Iterator[str]:
    """
    Stream file line by line.

    Args:
        file_path: Path to the file
        encoding: File encoding
        errors: Error handling strategy

    Yields:
        File lines as strings
    """
    streamer = FileStreamer()
    yield from streamer.stream_lines(file_path, encoding, errors)


def calculate_file_hash(
    file_path: Path,
    algorithm: str = 'sha256'
) -> str:
    """
    Calculate file hash with streaming.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use

    Returns:
        Hexadecimal hash string
    """
    streamer = FileStreamer()
    return streamer.calculate_hash(file_path, algorithm)