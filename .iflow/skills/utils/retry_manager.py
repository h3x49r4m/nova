"""Retry Manager - Automatic retry logic for failed operations.

This module provides configurable retry mechanisms with various backoff
strategies for handling transient failures.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Tuple

from .exceptions import IFlowError, ErrorCode, ErrorCategory


class BackoffStrategy(Enum):
    """Backoff strategies for retry attempts."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_WITH_JITTER = "exponential_with_jitter"
    CUSTOM = "custom"


class RetryOutcome(Enum):
    """Possible outcomes of a retry attempt."""
    SUCCESS = "success"
    MAX_ATTEMPTS_EXCEEDED = "max_attempts_exceeded"
    NON_RETRYABLE_ERROR = "non_retryable_error"
    TIMEOUT = "timeout"


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: float = 0.1
    retryable_errors: Optional[List[Type[Exception]]] = None
    retryable_error_codes: Optional[List[ErrorCode]] = None
    custom_backoff_fn: Optional[Callable[[int, float], float]] = None
    
    def __post_init__(self):
        """Initialize defaults."""
        if self.retryable_errors is None:
            self.retryable_errors = []
        if self.retryable_error_codes is None:
            self.retryable_error_codes = []
    
    def should_retry(self, error: Exception) -> bool:
        """
        Determine if an error should be retried.
        
        Args:
            error: The error that occurred
            
        Returns:
            True if the error should be retried
        """
        # Check if it's an IFlowError with TRANSIENT category
        if isinstance(error, IFlowError):
            if error.category == ErrorCategory.TRANSIENT:
                return True
            # Check specific error codes
            if error.code in self.retryable_error_codes:
                return True
            return False
        
        # Check exception types
        for error_type in self.retryable_errors:
            if isinstance(error, error_type):
                return True
        
        return False
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry attempt.
        
        Args:
            attempt: Current attempt number (1-indexed)
            
        Returns:
            Delay in seconds
        """
        if self.custom_backoff_fn:
            return min(self.custom_backoff_fn(attempt, self.base_delay), self.max_delay)
        
        if self.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.base_delay
        elif self.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.base_delay * attempt
        elif self.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.base_delay * (self.backoff_multiplier ** (attempt - 1))
        elif self.backoff_strategy == BackoffStrategy.EXPONENTIAL_WITH_JITTER:
            import random
            base_delay = self.base_delay * (self.backoff_multiplier ** (attempt - 1))
            jitter_amount = base_delay * self.jitter * (2 * random.random() - 1)
            delay = base_delay + jitter_amount
        else:
            delay = self.base_delay
        
        return min(max(0, delay), self.max_delay)


@dataclass
class RetryAttempt:
    """Record of a single retry attempt."""
    attempt_number: int
    timestamp: str
    error: Optional[Exception] = None
    delay_before: float = 0.0
    success: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert attempt to dictionary."""
        return {
            "attempt_number": self.attempt_number,
            "timestamp": self.timestamp,
            "error": str(self.error) if self.error else None,
            "delay_before": self.delay_before,
            "success": self.success
        }


@dataclass
class RetryResult:
    """Result of a retry operation."""
    outcome: RetryOutcome
    total_attempts: int
    attempts: List[RetryAttempt] = field(default_factory=list)
    result: Optional[Any] = None
    final_error: Optional[Exception] = None
    total_duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "outcome": self.outcome.value,
            "total_attempts": self.total_attempts,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "result": self.result,
            "final_error": str(self.final_error) if self.final_error else None,
            "total_duration": self.total_duration
        }


class RetryManager:
    """Manages retry logic for operations."""
    
    def __init__(self, default_policy: Optional[RetryPolicy] = None):
        """
        Initialize retry manager.
        
        Args:
            default_policy: Default retry policy to use
        """
        self.default_policy = default_policy or RetryPolicy()
        self.retry_history: List[RetryResult] = []
    
    def execute(
        self,
        fn: Callable,
        *args,
        policy: Optional[RetryPolicy] = None,
        **kwargs
    ) -> RetryResult:
        """
        Execute a function with retry logic.
        
        Args:
            fn: Function to execute
            *args: Positional arguments for the function
            policy: Retry policy to use (uses default if None)
            **kwargs: Keyword arguments for the function
            
        Returns:
            RetryResult with outcome and data
        """
        policy = policy or self.default_policy
        attempts = []
        start_time = time.time()
        last_error = None
        
        for attempt_num in range(1, policy.max_attempts + 1):
            attempt_start = time.time()
            delay_before = 0.0
            
            if attempt_num > 1:
                # Calculate delay before this attempt
                delay_before = policy.calculate_delay(attempt_num - 1)
                time.sleep(delay_before)
            
            try:
                # Execute the function
                result = fn(*args, **kwargs)
                
                # Record successful attempt
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    timestamp=datetime.now().isoformat(),
                    delay_before=delay_before,
                    success=True
                )
                attempts.append(attempt)
                
                # Calculate total duration
                total_duration = time.time() - start_time
                
                # Return successful result
                retry_result = RetryResult(
                    outcome=RetryOutcome.SUCCESS,
                    total_attempts=attempt_num,
                    attempts=attempts,
                    result=result,
                    total_duration=total_duration
                )
                
                self.retry_history.append(retry_result)
                return retry_result
                
            except Exception as e:
                last_error = e
                
                # Record failed attempt
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    timestamp=datetime.now().isoformat(),
                    error=e,
                    delay_before=delay_before,
                    success=False
                )
                attempts.append(attempt)
                
                # Check if we should retry
                if not policy.should_retry(e):
                    # Non-retryable error
                    total_duration = time.time() - start_time
                    retry_result = RetryResult(
                        outcome=RetryOutcome.NON_RETRYABLE_ERROR,
                        total_attempts=attempt_num,
                        attempts=attempts,
                        final_error=e,
                        total_duration=total_duration
                    )
                    self.retry_history.append(retry_result)
                    return retry_result
                
                # Check if we've exhausted max attempts
                if attempt_num >= policy.max_attempts:
                    total_duration = time.time() - start_time
                    retry_result = RetryResult(
                        outcome=RetryOutcome.MAX_ATTEMPTS_EXCEEDED,
                        total_attempts=attempt_num,
                        attempts=attempts,
                        final_error=e,
                        total_duration=total_duration
                    )
                    self.retry_history.append(retry_result)
                    return retry_result
                
                # Otherwise, continue to next attempt
                continue
        
        # This should never be reached, but just in case
        total_duration = time.time() - start_time
        retry_result = RetryResult(
            outcome=RetryOutcome.MAX_ATTEMPTS_EXCEEDED,
            total_attempts=len(attempts),
            attempts=attempts,
            final_error=last_error,
            total_duration=total_duration
        )
        self.retry_history.append(retry_result)
        return retry_result
    
    def execute_with_timeout(
        self,
        fn: Callable,
        *args,
        timeout: float = 30.0,
        policy: Optional[RetryPolicy] = None,
        **kwargs
    ) -> RetryResult:
        """
        Execute a function with retry logic and timeout.
        
        Args:
            fn: Function to execute
            *args: Positional arguments for the function
            timeout: Maximum time for each attempt in seconds
            policy: Retry policy to use
            **kwargs: Keyword arguments for the function
            
        Returns:
            RetryResult with outcome and data
        """
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Operation timed out after {timeout} seconds")
        
        # Set signal handler for timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        
        try:
            # Execute with timeout wrapper
            def timeout_wrapper(*inner_args, **inner_kwargs):
                signal.alarm(int(timeout))
                try:
                    return fn(*inner_args, **inner_kwargs)
                finally:
                    signal.alarm(0)
            
            return self.execute(timeout_wrapper, *args, policy=policy, **kwargs)
        finally:
            # Restore old handler
            signal.signal(signal.SIGALRM, old_handler)
    
    def get_retry_history(self, limit: int = 100) -> List[RetryResult]:
        """
        Get retry history.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of retry results
        """
        return self.retry_history[-limit:]
    
    def get_retry_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about retry operations.
        
        Returns:
            Dictionary with retry statistics
        """
        if not self.retry_history:
            return {
                "total_operations": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
                "avg_attempts": 0.0,
                "max_attempts": 0
            }
        
        successful = sum(1 for result in self.retry_history if result.outcome == RetryOutcome.SUCCESS)
        failed = len(self.retry_history) - successful
        avg_attempts = sum(result.total_attempts for result in self.retry_history) / len(self.retry_history)
        max_attempts = max(result.total_attempts for result in self.retry_history)
        
        return {
            "total_operations": len(self.retry_history),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(self.retry_history),
            "avg_attempts": avg_attempts,
            "max_attempts": max_attempts
        }
    
    def clear_history(self) -> None:
        """Clear retry history."""
        self.retry_history = []


def retry(
    max_attempts: int = 3,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_errors: Optional[List[Type[Exception]]] = None,
    retryable_error_codes: Optional[List[ErrorCode]] = None
):
    """
    Decorator for automatic retry logic.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_strategy: Backoff strategy to use
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        retryable_errors: List of exception types to retry
        retryable_error_codes: List of error codes to retry
        
    Returns:
        Decorator function
        
    Example:
        @retry(max_attempts=3, backoff_strategy=BackoffStrategy.EXPONENTIAL)
        def fetch_data(url):
            # May fail transiently
            return requests.get(url)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            policy = RetryPolicy(
                max_attempts=max_attempts,
                backoff_strategy=backoff_strategy,
                base_delay=base_delay,
                max_delay=max_delay,
                retryable_errors=retryable_errors,
                retryable_error_codes=retryable_error_codes
            )
            
            manager = RetryManager(policy)
            result = manager.execute(func, *args, policy=policy, **kwargs)
            
            if result.outcome == RetryOutcome.SUCCESS:
                return result.result
            else:
                # Raise the final error
                if result.final_error:
                    raise result.final_error
                else:
                    raise IFlowError(
                        "Operation failed after retry attempts",
                        ErrorCode.OPERATION_FAILED
                    )
        
        return wrapper
    return decorator


# Predefined retry policies for common scenarios

RETRY_POLICY_NETWORK = RetryPolicy(
    max_attempts=5,
    backoff_strategy=BackoffStrategy.EXPONENTIAL_WITH_JITTER,
    base_delay=1.0,
    max_delay=30.0,
    retryable_error_codes=[ErrorCode.TIMEOUT]
)

RETRY_POLICY_DATABASE = RetryPolicy(
    max_attempts=3,
    backoff_strategy=BackoffStrategy.EXPONENTIAL,
    base_delay=0.5,
    max_delay=10.0
)

RETRY_POLICY_EXTERNAL_API = RetryPolicy(
    max_attempts=4,
    backoff_strategy=BackoffStrategy.EXPONENTIAL_WITH_JITTER,
    base_delay=2.0,
    max_delay=60.0
)

RETRY_POLICY_FILE_IO = RetryPolicy(
    max_attempts=3,
    backoff_strategy=BackoffStrategy.LINEAR,
    base_delay=0.1,
    max_delay=1.0
)