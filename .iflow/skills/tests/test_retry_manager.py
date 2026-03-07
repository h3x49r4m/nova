"""Tests for retry manager system."""

import time
from unittest.mock import patch, MagicMock

import pytest

from utils.retry_manager import (
    BackoffStrategy,
    RetryOutcome,
    RetryPolicy,
    RetryAttempt,
    RetryResult,
    RetryManager,
    retry,
    RETRY_POLICY_NETWORK,
    RETRY_POLICY_DATABASE,
    RETRY_POLICY_EXTERNAL_API,
    RETRY_POLICY_FILE_IO
)
from utils.exceptions import IFlowError, ErrorCode, ErrorCategory


class TestBackoffStrategy:
    """Test BackoffStrategy enum."""
    
    def test_strategies(self):
        """Test all backoff strategies exist."""
        assert BackoffStrategy.FIXED.value == "fixed"
        assert BackoffStrategy.LINEAR.value == "linear"
        assert BackoffStrategy.EXPONENTIAL.value == "exponential"
        assert BackoffStrategy.EXPONENTIAL_WITH_JITTER.value == "exponential_with_jitter"
        assert BackoffStrategy.CUSTOM.value == "custom"


class TestRetryOutcome:
    """Test RetryOutcome enum."""
    
    def test_outcomes(self):
        """Test all retry outcomes exist."""
        assert RetryOutcome.SUCCESS.value == "success"
        assert RetryOutcome.MAX_ATTEMPTS_EXCEEDED.value == "max_attempts_exceeded"
        assert RetryOutcome.NON_RETRYABLE_ERROR.value == "non_retryable_error"
        assert RetryOutcome.TIMEOUT.value == "timeout"


class TestRetryPolicy:
    """Test RetryPolicy dataclass."""
    
    def test_default_policy(self):
        """Test creating default retry policy."""
        policy = RetryPolicy()
        
        assert policy.max_attempts == 3
        assert policy.backoff_strategy == BackoffStrategy.EXPONENTIAL
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.retryable_errors == []
        assert policy.retryable_error_codes == []
    
    def test_custom_policy(self):
        """Test creating custom retry policy."""
        policy = RetryPolicy(
            max_attempts=5,
            backoff_strategy=BackoffStrategy.LINEAR,
            base_delay=2.0,
            retryable_error_codes=[ErrorCode.TIMEOUT]
        )
        
        assert policy.max_attempts == 5
        assert policy.backoff_strategy == BackoffStrategy.LINEAR
        assert policy.base_delay == 2.0
        assert policy.retryable_error_codes == [ErrorCode.TIMEOUT]
    
    def test_should_retry_transient_error(self):
        """Test should_retry for transient errors."""
        policy = RetryPolicy()
        
        error = IFlowError(
            "Transient error",
            ErrorCode.TIMEOUT,
            ErrorCategory.TRANSIENT
        )
        
        assert policy.should_retry(error) is True
    
    def test_should_retry_permanent_error(self):
        """Test should_retry for permanent errors."""
        policy = RetryPolicy()
        
        error = IFlowError(
            "Permanent error",
            ErrorCode.VALIDATION_FAILED,
            ErrorCategory.PERMANENT
        )
        
        assert policy.should_retry(error) is False
    
    def test_should_retry_specific_error_code(self):
        """Test should_retry for specific error codes."""
        policy = RetryPolicy(
            retryable_error_codes=[ErrorCode.TIMEOUT]
        )
        
        error = IFlowError(
            "Timeout error",
            ErrorCode.TIMEOUT,
            ErrorCategory.PERMANENT  # Even though permanent, code is retryable
        )
        
        assert policy.should_retry(error) is True
    
    def test_should_retry_exception_type(self):
        """Test should_retry for specific exception types."""
        policy = RetryPolicy(
            retryable_errors=[ConnectionError]
        )
        
        error = ConnectionError("Connection failed")
        
        assert policy.should_retry(error) is True
    
    def test_calculate_delay_fixed(self):
        """Test delay calculation for fixed strategy."""
        policy = RetryPolicy(
            backoff_strategy=BackoffStrategy.FIXED,
            base_delay=2.0
        )
        
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(2) == 2.0
        assert policy.calculate_delay(3) == 2.0
    
    def test_calculate_delay_linear(self):
        """Test delay calculation for linear strategy."""
        policy = RetryPolicy(
            backoff_strategy=BackoffStrategy.LINEAR,
            base_delay=1.0
        )
        
        assert policy.calculate_delay(1) == 1.0
        assert policy.calculate_delay(2) == 2.0
        assert policy.calculate_delay(3) == 3.0
    
    def test_calculate_delay_exponential(self):
        """Test delay calculation for exponential strategy."""
        policy = RetryPolicy(
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            base_delay=1.0,
            backoff_multiplier=2.0
        )
        
        assert policy.calculate_delay(1) == 1.0
        assert policy.calculate_delay(2) == 2.0
        assert policy.calculate_delay(3) == 4.0
    
    def test_calculate_delay_max_delay(self):
        """Test delay calculation respects max_delay."""
        policy = RetryPolicy(
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            base_delay=10.0,
            max_delay=15.0,
            backoff_multiplier=2.0
        )
        
        assert policy.calculate_delay(1) == 10.0
        assert policy.calculate_delay(2) == 15.0  # Capped at max_delay
        assert policy.calculate_delay(3) == 15.0  # Capped at max_delay
    
    def test_calculate_delay_custom(self):
        """Test delay calculation with custom function."""
        def custom_delay(attempt, base):
            return base * attempt * 1.5
        
        policy = RetryPolicy(
            backoff_strategy=BackoffStrategy.CUSTOM,
            base_delay=2.0,
            custom_backoff_fn=custom_delay
        )
        
        assert policy.calculate_delay(1) == 3.0
        assert policy.calculate_delay(2) == 6.0
        assert policy.calculate_delay(3) == 9.0


class TestRetryAttempt:
    """Test RetryAttempt dataclass."""
    
    def test_attempt_creation(self):
        """Test creating retry attempt."""
        attempt = RetryAttempt(
            attempt_number=1,
            timestamp="2024-01-01T00:00:00",
            success=True
        )
        
        assert attempt.attempt_number == 1
        assert attempt.timestamp == "2024-01-01T00:00:00"
        assert attempt.success is True
        assert attempt.error is None
    
    def test_attempt_with_error(self):
        """Test creating retry attempt with error."""
        error = Exception("Test error")
        attempt = RetryAttempt(
            attempt_number=2,
            timestamp="2024-01-01T00:00:00",
            error=error,
            delay_before=1.0,
            success=False
        )
        
        assert attempt.attempt_number == 2
        assert attempt.error == error
        assert attempt.delay_before == 1.0
        assert attempt.success is False
    
    def test_attempt_to_dict(self):
        """Test converting attempt to dictionary."""
        error = Exception("Test error")
        attempt = RetryAttempt(
            attempt_number=1,
            timestamp="2024-01-01T00:00:00",
            error=error,
            delay_before=0.5,
            success=False
        )
        
        data = attempt.to_dict()
        
        assert data["attempt_number"] == 1
        assert data["timestamp"] == "2024-01-01T00:00:00"
        assert data["error"] == "Test error"
        assert data["delay_before"] == 0.5
        assert data["success"] is False


class TestRetryResult:
    """Test RetryResult dataclass."""
    
    def test_result_creation(self):
        """Test creating retry result."""
        result = RetryResult(
            outcome=RetryOutcome.SUCCESS,
            total_attempts=1,
            result="success_value"
        )
        
        assert result.outcome == RetryOutcome.SUCCESS
        assert result.total_attempts == 1
        assert result.result == "success_value"
        assert result.final_error is None
    
    def test_result_with_error(self):
        """Test creating retry result with error."""
        error = Exception("Final error")
        result = RetryResult(
            outcome=RetryOutcome.MAX_ATTEMPTS_EXCEEDED,
            total_attempts=3,
            final_error=error
        )
        
        assert result.outcome == RetryOutcome.MAX_ATTEMPTS_EXCEEDED
        assert result.final_error == error
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        error = Exception("Test error")
        attempt = RetryAttempt(
            attempt_number=1,
            timestamp="2024-01-01T00:00:00",
            success=False
        )
        
        result = RetryResult(
            outcome=RetryOutcome.MAX_ATTEMPTS_EXCEEDED,
            total_attempts=3,
            attempts=[attempt],
            final_error=error,
            total_duration=5.0
        )
        
        data = result.to_dict()
        
        assert data["outcome"] == "max_attempts_exceeded"
        assert data["total_attempts"] == 3
        assert len(data["attempts"]) == 1
        assert data["final_error"] == "Test error"
        assert data["total_duration"] == 5.0


class TestRetryManager:
    """Test RetryManager."""
    
    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = RetryManager()
        
        assert manager.default_policy.max_attempts == 3
        assert manager.retry_history == []
    
    def test_execute_success(self):
        """Test executing function that succeeds immediately."""
        manager = RetryManager()
        
        def success_fn():
            return "success"
        
        result = manager.execute(success_fn)
        
        assert result.outcome == RetryOutcome.SUCCESS
        assert result.total_attempts == 1
        assert result.result == "success"
        assert len(result.attempts) == 1
        assert result.attempts[0].success is True
    
    def test_execute_retry_success(self):
        """Test executing function that fails then succeeds on retry."""
        manager = RetryManager(
            RetryPolicy(
                max_attempts=3,
                retryable_errors=[ValueError]
            )
        )
        
        attempt_count = 0
        
        def flaky_fn():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary error")
            return "success"
        
        result = manager.execute(flaky_fn)
        
        assert result.outcome == RetryOutcome.SUCCESS
        assert result.total_attempts == 2
        assert result.result == "success"
        assert len(result.attempts) == 2
        assert result.attempts[0].success is False
        assert result.attempts[1].success is True
    
    def test_execute_max_attempts_exceeded(self):
        """Test executing function that fails all attempts."""
        manager = RetryManager(
            RetryPolicy(
                max_attempts=2,
                retryable_errors=[ValueError]
            )
        )
        
        def failing_fn():
            raise ValueError("Always fails")
        
        result = manager.execute(failing_fn)
        
        assert result.outcome == RetryOutcome.MAX_ATTEMPTS_EXCEEDED
        assert result.total_attempts == 2
        assert result.final_error is not None
        assert isinstance(result.final_error, ValueError)
    
    def test_execute_non_retryable_error(self):
        """Test executing function that fails with non-retryable error."""
        manager = RetryManager(
            RetryPolicy(
                max_attempts=5,
                retryable_errors=[ValueError]
            )
        )
        
        def failing_fn():
            raise TypeError("Non-retryable error")
        
        result = manager.execute(failing_fn)
        
        assert result.outcome == RetryOutcome.NON_RETRYABLE_ERROR
        assert result.total_attempts == 1  # Should not retry
        assert result.final_error is not None
        assert isinstance(result.final_error, TypeError)
    
    def test_execute_with_args(self):
        """Test executing function with arguments."""
        manager = RetryManager()
        
        def add(a, b):
            return a + b
        
        result = manager.execute(add, 2, 3)
        
        assert result.outcome == RetryOutcome.SUCCESS
        assert result.result == 5
    
    def test_execute_with_kwargs(self):
        """Test executing function with keyword arguments."""
        manager = RetryManager()
        
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"
        
        result = manager.execute(greet, name="World", greeting="Hi")
        
        assert result.outcome == RetryOutcome.SUCCESS
        assert result.result == "Hi, World!"
    
    def test_get_retry_history(self):
        """Test getting retry history."""
        manager = RetryManager()
        
        def success_fn():
            return "success"
        
        manager.execute(success_fn)
        manager.execute(success_fn)
        manager.execute(success_fn)
        
        history = manager.get_retry_history()
        
        assert len(history) == 3
    
    def test_get_retry_history_limit(self):
        """Test getting retry history with limit."""
        manager = RetryManager()
        
        def success_fn():
            return "success"
        
        for _ in range(5):
            manager.execute(success_fn)
        
        history = manager.get_retry_history(limit=3)
        
        assert len(history) == 3
    
    def test_get_retry_statistics(self):
        """Test getting retry statistics."""
        manager = RetryManager()
        
        def success_fn():
            return "success"
        
        manager.execute(success_fn)
        manager.execute(success_fn)
        
        stats = manager.get_retry_statistics()
        
        assert stats["total_operations"] == 2
        assert stats["successful"] == 2
        assert stats["failed"] == 0
        assert stats["success_rate"] == 1.0
        assert stats["avg_attempts"] == 1.0
    
    def test_get_retry_statistics_empty(self):
        """Test getting retry statistics with no history."""
        manager = RetryManager()
        
        stats = manager.get_retry_statistics()
        
        assert stats["total_operations"] == 0
        assert stats["successful"] == 0
        assert stats["failed"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_attempts"] == 0.0
    
    def test_clear_history(self):
        """Test clearing retry history."""
        manager = RetryManager()
        
        def success_fn():
            return "success"
        
        manager.execute(success_fn)
        manager.clear_history()
        
        assert len(manager.retry_history) == 0
    
    def test_delay_between_retries(self):
        """Test that delays are applied between retries."""
        policy = RetryPolicy(
            max_attempts=3,
            backoff_strategy=BackoffStrategy.FIXED,
            base_delay=0.1,  # 100ms delay
            retryable_errors=[ValueError]
        )
        manager = RetryManager(policy)
        
        attempt_count = 0
        
        def flaky_fn():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        start_time = time.time()
        result = manager.execute(flaky_fn)
        elapsed = time.time() - start_time
        
        assert result.outcome == RetryOutcome.SUCCESS
        # Should have at least 2 delays (after attempt 1 and 2)
        assert elapsed >= 0.2  # 2 * 0.1 seconds
    
    def test_custom_policy_in_execute(self):
        """Test using custom policy in execute."""
        manager = RetryManager()
        
        custom_policy = RetryPolicy(
            max_attempts=5,
            retryable_errors=[ValueError]
        )
        
        attempt_count = 0
        
        def flaky_fn():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 4:
                raise ValueError("Temporary error")
            return "success"
        
        result = manager.execute(flaky_fn, policy=custom_policy)
        
        assert result.outcome == RetryOutcome.SUCCESS
        assert result.total_attempts == 4


class TestRetryDecorator:
    """Test retry decorator."""
    
    def test_retry_decorator_success(self):
        """Test retry decorator on successful function."""
        @retry(max_attempts=3)
        def success_fn():
            return "success"
        
        result = success_fn()
        
        assert result == "success"
    
    def test_retry_decorator_retry_success(self):
        """Test retry decorator on function that succeeds on retry."""
        attempt_count = 0
        
        @retry(max_attempts=3, retryable_errors=[ValueError])
        def flaky_fn():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Temporary error")
            return "success"
        
        result = flaky_fn()
        
        assert result == "success"
        assert attempt_count == 2
    
    def test_retry_decorator_max_attempts(self):
        """Test retry decorator when max attempts exceeded."""
        @retry(max_attempts=2, retryable_errors=[ValueError])
        def failing_fn():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError) as exc_info:
            failing_fn()
        
        assert str(exc_info.value) == "Always fails"
    
    def test_retry_decorator_custom_backoff(self):
        """Test retry decorator with custom backoff."""
        @retry(
            max_attempts=3,
            backoff_strategy=BackoffStrategy.LINEAR,
            base_delay=0.01
        )
        def flaky_fn():
            raise ValueError("Error")
        
        with pytest.raises(ValueError):
            flaky_fn()


class TestPredefinedPolicies:
    """Test predefined retry policies."""
    
    def test_network_policy(self):
        """Test network retry policy."""
        assert RETRY_POLICY_NETWORK.max_attempts == 5
        assert RETRY_POLICY_NETWORK.backoff_strategy == BackoffStrategy.EXPONENTIAL_WITH_JITTER
        assert RETRY_POLICY_NETWORK.retryable_error_codes == [ErrorCode.TIMEOUT]
    
    def test_database_policy(self):
        """Test database retry policy."""
        assert RETRY_POLICY_DATABASE.max_attempts == 3
        assert RETRY_POLICY_DATABASE.backoff_strategy == BackoffStrategy.EXPONENTIAL
        assert RETRY_POLICY_DATABASE.base_delay == 0.5
    
    def test_external_api_policy(self):
        """Test external API retry policy."""
        assert RETRY_POLICY_EXTERNAL_API.max_attempts == 4
        assert RETRY_POLICY_EXTERNAL_API.backoff_strategy == BackoffStrategy.EXPONENTIAL_WITH_JITTER
        assert RETRY_POLICY_EXTERNAL_API.base_delay == 2.0
    
    def test_file_io_policy(self):
        """Test file I/O retry policy."""
        assert RETRY_POLICY_FILE_IO.max_attempts == 3
        assert RETRY_POLICY_FILE_IO.backoff_strategy == BackoffStrategy.LINEAR
        assert RETRY_POLICY_FILE_IO.base_delay == 0.1