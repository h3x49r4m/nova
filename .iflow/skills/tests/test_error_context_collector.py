"""Tests for enhanced error context collector."""

import os
from pathlib import Path

import pytest

from utils.error_context_collector import (
    ErrorContext,
    ErrorContextCollector,
    collect_error_context,
    with_error_context,
    error_context
)
from utils.exceptions import IFlowError, ErrorCode


class TestErrorContext:
    """Test ErrorContext dataclass."""
    
    def test_context_initialization(self):
        """Test creating an empty error context."""
        context = ErrorContext()
        
        assert context.timestamp == ""
        assert context.system_info == {}
        assert context.environment == {}
        assert context.call_stack == []
        assert context.variables == {}
        assert context.files == {}
        assert context.process_info == {}
        assert context.thread_info == {}
        assert context.network_info == {}
        assert context.disk_info == {}
        assert context.memory_info == {}
        assert context.performance_metrics == {}
        assert context.custom_context == {}
    
    def test_context_to_dict(self):
        """Test converting context to dictionary."""
        context = ErrorContext()
        context.timestamp = "2024-01-01T00:00:00"
        context.system_info = {"python_version": "3.9"}
        
        data = context.to_dict()
        
        assert data["timestamp"] == "2024-01-01T00:00:00"
        assert data["system_info"] == {"python_version": "3.9"}
        assert "thread_info" in data
        assert "network_info" in data
        assert "disk_info" in data
        assert "memory_info" in data
        assert "performance_metrics" in data


class TestErrorContextCollector:
    """Test ErrorContextCollector."""
    
    def test_collector_initialization(self):
        """Test collector initialization."""
        collector = ErrorContextCollector()
        
        assert collector.repo_root == Path.cwd()
        assert collector.collect_system_info is True
        assert collector.collect_environment is True
        assert collector.collect_call_stack is True
        assert collector.collect_variables is True
        assert collector.collect_thread_info is True
        assert collector.collect_network_info is False
        assert collector.collect_disk_info is False
        assert collector.collect_performance_metrics is True
    
    def test_collector_custom_initialization(self):
        """Test collector with custom settings."""
        collector = ErrorContextCollector(
            repo_root=Path("/tmp"),
            collect_system_info=False,
            collect_network_info=True,
            collect_disk_info=True,
            max_stack_frames=10
        )
        
        assert collector.repo_root == Path("/tmp")
        assert collector.collect_system_info is False
        assert collector.collect_network_info is True
        assert collector.collect_disk_info is True
        assert collector.max_stack_frames == 10
    
    def test_collect_all_context(self):
        """Test collecting all error context."""
        collector = ErrorContextCollector()
        error = ValueError("Test error")
        
        context = collector.collect(error)
        
        assert context.timestamp != ""
        assert context.system_info != {}
        assert isinstance(context.environment, dict)
        assert isinstance(context.call_stack, list)
        assert isinstance(context.variables, dict)
        assert context.process_info != {}
        assert context.thread_info != {}
        assert isinstance(context.performance_metrics, dict)
    
    def test_collect_minimal_context(self):
        """Test collecting minimal error context."""
        collector = ErrorContextCollector(
            collect_system_info=False,
            collect_environment=False,
            collect_call_stack=False,
            collect_variables=False,
            collect_thread_info=False,
            collect_performance_metrics=False
        )
        error = ValueError("Test error")
        
        context = collector.collect(error)
        
        assert context.timestamp != ""
        assert context.system_info == {}
        assert context.environment == {}
        assert context.call_stack == []
        assert context.variables == {}
        assert context.thread_info == {}
        assert context.performance_metrics == {}
    
    def test_collect_system_info(self):
        """Test system info collection."""
        collector = ErrorContextCollector()
        
        system_info = collector._collect_system_info()
        
        assert "platform" in system_info
        assert "system" in system_info
        assert "python_version" in system_info
        assert "hostname" in system_info
    
    def test_collect_environment(self):
        """Test environment collection."""
        collector = ErrorContextCollector()
        
        # Set a test environment variable
        os.environ["TEST_VAR"] = "test_value"
        
        env = collector._collect_environment()
        
        # Test that non-sensitive vars are collected
        assert "TEST_VAR" in env
        
        # Clean up
        del os.environ["TEST_VAR"]
    
    def test_collect_environment_filters_sensitive(self):
        """Test that sensitive environment variables are filtered."""
        collector = ErrorContextCollector()
        
        # Set a sensitive environment variable
        os.environ["TEST_PASSWORD"] = "secret123"
        
        env = collector._collect_environment()
        
        # Should be filtered out
        assert "TEST_PASSWORD" not in env
        
        # Clean up
        del os.environ["TEST_PASSWORD"]
    
    def test_collect_call_stack(self):
        """Test call stack collection."""
        collector = ErrorContextCollector()
        
        call_stack = collector._collect_call_stack(skip_frames=0)
        
        assert isinstance(call_stack, list)
        # Should have some frames
        assert len(call_stack) > 0
    
    def test_collect_call_stack_skip_frames(self):
        """Test call stack collection with skip frames."""
        collector = ErrorContextCollector(max_stack_frames=50)
        
        call_stack_no_skip = collector._collect_call_stack(skip_frames=0)
        call_stack_skip = collector._collect_call_stack(skip_frames=2)
        
        # Skipping frames should result in fewer frames (or at least different frames)
        assert len(call_stack_skip) <= len(call_stack_no_skip)
        # The first frame should be different
        if call_stack_skip and call_stack_no_skip:
            assert call_stack_skip[0] != call_stack_no_skip[0]
    
    def test_collect_variables(self):
        """Test variable collection."""
        collector = ErrorContextCollector()
        
        variables = collector._collect_variables()
        
        assert isinstance(variables, dict)
    
    def test_sanitize_variables(self):
        """Test variable sanitization."""
        collector = ErrorContextCollector()
        
        variables = {
            "normal_var": "value",
            "_private_var": "private",
            "self": "object",
            "password": "secret",  # Should be filtered
            "list_var": [1, 2, 3],
            "dict_var": {"key": "value"}
        }
        
        sanitized = collector._sanitize_variables(variables)
        
        # Normal variable should be present
        assert "normal_var" in sanitized
        
        # Private variable should be skipped
        assert "_private_var" not in sanitized
        
        # Special variable should be skipped
        assert "self" not in sanitized
        
        # Sensitive variable should be skipped
        assert "password" not in sanitized
        
        # List and dict should be present
        assert "list_var" in sanitized
        assert "dict_var" in sanitized
    
    def test_sanitize_value_primitives(self):
        """Test sanitizing primitive values."""
        collector = ErrorContextCollector()
        
        assert collector._sanitize_value(None, 0) is None
        assert collector._sanitize_value(True, 0) is True
        assert collector._sanitize_value(42, 0) == 42
        assert collector._sanitize_value(3.14, 0) == 3.14
    
    def test_sanitize_value_string(self):
        """Test sanitizing string values."""
        collector = ErrorContextCollector()
        
        short_string = "hello"
        long_string = "a" * 300
        
        assert collector._sanitize_value(short_string, 0) == "hello"
        assert "truncated" in collector._sanitize_value(long_string, 0)
    
    def test_sanitize_value_collections(self):
        """Test sanitizing collection values."""
        collector = ErrorContextCollector()
        
        assert collector._sanitize_value([1, 2, 3], 0) == [1, 2, 3]
        assert collector._sanitize_value({"key": "value"}, 0) == {"key": "value"}
        assert collector._sanitize_value({1, 2, 3}, 0) == [1, 2, 3]
    
    def test_sanitize_value_objects(self):
        """Test sanitizing object values."""
        collector = ErrorContextCollector()
        
        obj = object()
        result = collector._sanitize_value(obj, 0)
        
        assert "object" in result
    
    def test_sanitize_value_bytes(self):
        """Test sanitizing bytes values."""
        collector = ErrorContextCollector()
        
        byte_data = b"test data"
        result = collector._sanitize_value(byte_data, 0)
        
        assert "bytes" in result
        assert "9" in result  # length of byte_data
    
    def test_collect_process_info(self):
        """Test process info collection."""
        collector = ErrorContextCollector()
        
        process_info = collector._collect_process_info()
        
        assert "pid" in process_info
        assert process_info["pid"] == os.getpid()
    
    def test_collect_thread_info(self):
        """Test thread info collection."""
        collector = ErrorContextCollector()
        
        thread_info = collector._collect_thread_info()
        
        assert "current_thread" in thread_info
        assert "total_threads" in thread_info
        assert "active_threads" in thread_info
        assert thread_info["total_threads"] > 0
    
    def test_collect_memory_info(self):
        """Test memory info collection."""
        collector = ErrorContextCollector()
        
        memory_info = collector._collect_memory_info()
        
        # Should have either memory info or error
        assert memory_info is not None
    
    def test_collect_performance_metrics(self):
        """Test performance metrics collection."""
        collector = ErrorContextCollector()
        
        metrics = collector._collect_performance_metrics()
        
        assert "duration_seconds" in metrics
        assert "timestamp" in metrics
        assert metrics["duration_seconds"] >= 0
    
    def test_collect_file_info(self):
        """Test file info collection."""
        collector = ErrorContextCollector()
        
        file_info = collector._collect_file_info()
        
        assert "repository" in file_info
        assert file_info["repository"]["path"] == str(collector.repo_root)
    
    def test_collect_with_custom_context(self):
        """Test collecting with custom context."""
        collector = ErrorContextCollector()
        error = ValueError("Test error")
        custom_context = {"custom_key": "custom_value"}
        
        context = collector.collect(error, custom_context=custom_context)
        
        assert context.custom_context == custom_context
    
    def test_sensitive_keys_filtering(self):
        """Test that sensitive keys are properly filtered."""
        collector = ErrorContextCollector()
        
        # Check default sensitive keys
        assert "PASSWORD" in collector.sensitive_keys
        assert "SECRET" in collector.sensitive_keys
        assert "TOKEN" in collector.sensitive_keys


class TestCollectErrorContext:
    """Test collect_error_context function."""
    
    def test_collect_error_context_basic(self):
        """Test basic error context collection."""
        error = ValueError("Test error")
        
        context = collect_error_context(error)
        
        assert context.timestamp != ""
        assert context.system_info != {}
    
    def test_collect_error_context_with_repo_root(self):
        """Test error context collection with custom repo root."""
        error = ValueError("Test error")
        repo_root = Path("/tmp")
        
        context = collect_error_context(error, repo_root=repo_root)
        
        assert context.files["repository"]["path"] == str(repo_root)
    
    def test_collect_error_context_with_custom_options(self):
        """Test error context collection with custom options."""
        error = ValueError("Test error")
        
        context = collect_error_context(
            error,
            collect_system_info=False,
            collect_network_info=True
        )
        
        assert context.system_info == {}
        # Network info might be empty if psutil not available, but key should exist
        assert "network_info" in context.__dict__


class TestWithErrorContextDecorator:
    """Test with_error_context decorator."""
    
    def test_decorator_success(self):
        """Test decorator when function succeeds."""
        @with_error_context()
        def success_fn():
            return "success"
        
        result = success_fn()
        
        assert result == "success"
    
    def test_decorator_failure(self):
        """Test decorator when function fails."""
        @with_error_context()
        def failing_fn():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_fn()
    
    def test_decorator_with_iflow_error(self):
        """Test decorator with IFlowError."""
        @with_error_context()
        def failing_fn():
            raise IFlowError("Test error", ErrorCode.VALIDATION_FAILED)
        
        with pytest.raises(IFlowError) as exc_info:
            failing_fn()
        
        # Check that context was attached
        assert hasattr(exc_info.value, "context")
        assert exc_info.value.context is not None
    
    def test_decorator_custom_options(self):
        """Test decorator with custom options."""
        @with_error_context(
            collect_system_info=False,
            collect_variables=False
        )
        def failing_fn():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_fn()


class TestErrorContextManager:
    """Test ErrorContextManager."""
    
    def test_context_manager_success(self):
        """Test context manager when no error occurs."""
        with error_context() as collector:
            assert collector is not None
            result = "success"
        
        assert result == "success"
    
    def test_context_manager_failure(self):
        """Test context manager when error occurs."""
        with pytest.raises(ValueError):
            with error_context() as collector:
                assert collector is not None
                raise ValueError("Test error")
    
    def test_context_manager_with_iflow_error(self):
        """Test context manager with IFlowError."""
        try:
            with error_context() as collector:
                assert collector is not None
                raise IFlowError("Test error", ErrorCode.VALIDATION_FAILED)
        except IFlowError as e:
            # Check that context was attached
            assert hasattr(e, "context")
            assert e.context is not None
    
    def test_context_manager_custom_repo_root(self):
        """Test context manager with custom repo root."""
        repo_root = Path("/tmp")
        
        with error_context(repo_root=repo_root) as collector:
            assert collector.repo_root == repo_root


class TestIntegration:
    """Integration tests for error context collector."""
    
    def test_full_context_collection(self):
        """Test full context collection with all options enabled."""
        error = ValueError("Test error")
        
        context = collect_error_context(
            error,
            collect_system_info=True,
            collect_environment=True,
            collect_call_stack=True,
            collect_variables=True,
            collect_thread_info=True,
            collect_network_info=True,
            collect_disk_info=True,
            collect_performance_metrics=True
        )
        
        # Verify all context is collected
        assert context.timestamp != ""
        assert context.system_info != {}
        assert isinstance(context.environment, dict)
        assert isinstance(context.call_stack, list)
        assert isinstance(context.variables, dict)
        assert context.process_info != {}
        assert context.thread_info != {}
        # Network and disk info might be empty if psutil not available
        assert isinstance(context.network_info, dict)
        assert isinstance(context.disk_info, dict)
        assert isinstance(context.memory_info, dict)
        assert context.performance_metrics != {}
    
    def test_context_serialization(self):
        """Test that context can be serialized to dict."""
        error = ValueError("Test error")
        
        context = collect_error_context(error)
        context_dict = context.to_dict()
        
        # Verify structure
        assert isinstance(context_dict, dict)
        assert "timestamp" in context_dict
        assert "system_info" in context_dict
        assert "environment" in context_dict
        assert "call_stack" in context_dict
        assert "variables" in context_dict
        assert "files" in context_dict
        assert "process_info" in context_dict
        assert "thread_info" in context_dict
        assert "network_info" in context_dict
        assert "disk_info" in context_dict
        assert "memory_info" in context_dict
        assert "performance_metrics" in context_dict
        assert "custom_context" in context_dict
    
    def test_context_with_nested_error(self):
        """Test context collection with nested error."""
        def inner_function():
            raise ValueError("Inner error")
        
        def outer_function():
            try:
                inner_function()
            except ValueError as e:
                raise RuntimeError("Outer error") from e
        
        try:
            outer_function()
        except RuntimeError as error:
            context = collect_error_context(error)
            
            # Should have call stack with multiple frames
            assert len(context.call_stack) > 0
    
    def test_context_with_large_data(self):
        """Test context collection with large data structures."""
        error = ValueError("Test error")
        
        large_list = list(range(1000))
        large_dict = {f"key_{i}": f"value_{i}" for i in range(100)}
        
        context = collect_error_context(
            error,
            custom_context={
                "large_list": large_list,
                "large_dict": large_dict
            }
        )
        
        # Large data should be truncated
        assert context.custom_context is not None
        # The custom context is stored as-is, but variables are sanitized
        assert "large_list" in context.custom_context
        assert "large_dict" in context.custom_context