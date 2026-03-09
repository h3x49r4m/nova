"""Error Recovery Decorator.

This module provides decorators for applying consistent error recovery
patterns across skill implementations.
"""

import functools
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass

# Import error handling utilities
from .exceptions import IFlowError, ErrorCode
from .error_recovery_strategies import (
    RecoveryStrategyType,
    RecoveryStatus,
    RecoveryAttempt,
    RecoveryResult
)
from .structured_logger import StructuredLogger


@dataclass
class RecoveryConfig:
    """Configuration for error recovery."""
    max_attempts: int = 3
    backoff_factor: float = 2.0
    initial_delay: float = 1.0
    fallback_value: Any = None
    rollback_func: Optional[Callable] = None
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    retry_on_transient: bool = True
    retry_on_permanent: bool = False
    log_errors: bool = True


class ErrorRecoveryContext:
    """Context for tracking error recovery attempts."""
    
    def __init__(self, config: RecoveryConfig, logger: Optional[StructuredLogger] = None):
        """
        Initialize recovery context.
        
        Args:
            config: Recovery configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger
        self.attempts: List[RecoveryAttempt] = []
        self.circuit_breaker_failures: int = 0
        self.circuit_breaker_open_until: Optional[float] = None
    
    def record_attempt(
        self,
        strategy_type: RecoveryStrategyType,
        error: Optional[Exception] = None,
        recovery_time: float = 0.0,
        status: RecoveryStatus = RecoveryStatus.SUCCESS,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Record a recovery attempt.
        
        Args:
            strategy_type: Type of recovery strategy used
            error: Error that occurred (if any)
            recovery_time: Time taken for recovery
            status: Status of the recovery attempt
            details: Additional details
        """
        attempt = RecoveryAttempt(
            attempt_id=f"attempt_{len(self.attempts) + 1}",
            strategy_type=strategy_type,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            status=status,
            error=error,
            recovery_time=recovery_time,
            details=details or {}
        )
        self.attempts.append(attempt)
        
        if self.logger:
            self.logger.info(
                f"Recovery attempt recorded: {strategy_type.value}",
                extra={
                    'strategy_type': strategy_type.value,
                    'status': status.value,
                    'error': str(error) if error else None,
                    'recovery_time': recovery_time
                }
            )
    
    def should_retry(self, error: Exception) -> bool:
        """
        Determine if error should trigger a retry.
        
        Args:
            error: The error that occurred
            
        Returns:
            True if should retry, False otherwise
        """
        # Check circuit breaker
        if self.circuit_breaker_open_until:
            if time.time() < self.circuit_breaker_open_until:
                return False
            else:
                # Reset circuit breaker
                self.circuit_breaker_failures = 0
                self.circuit_breaker_open_until = None
        
        # Check error type
        if isinstance(error, IFlowError):
            if error.category.name == 'TRANSIENT' and self.config.retry_on_transient:
                return True
            elif error.category.name == 'PERMANENT' and self.config.retry_on_permanent:
                return True
            return False
        
        # For non-IFlowErrors, retry if configured
        return self.config.retry_on_transient
    
    def trigger_circuit_breaker(self):
        """Trigger circuit breaker after threshold failures."""
        if self.circuit_breaker_failures >= self.config.circuit_breaker_threshold:
            self.circuit_breaker_open_until = time.time() + self.config.circuit_breaker_timeout
            if self.logger:
                self.logger.warning(
                    "Circuit breaker triggered",
                    extra={
                        'failures': self.circuit_breaker_failures,
                        'timeout': self.config.circuit_breaker_timeout
                    }
                )
    
    def get_result(self, success: bool, final_value: Any = None, final_error: Optional[Exception] = None) -> RecoveryResult:
        """
        Get the final recovery result.
        
        Args:
            success: Whether recovery was successful
            final_value: Final value (if successful)
            final_error: Final error (if failed)
            
        Returns:
            RecoveryResult object
        """
        return RecoveryResult(
            success=success,
            attempts=self.attempts,
            final_value=final_value,
            final_error=final_error
        )


def with_error_recovery(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    fallback_value: Any = None,
    rollback_func: Optional[Callable] = None,
    circuit_breaker_threshold: int = 5,
    circuit_breaker_timeout: float = 60.0,
    retry_on_transient: bool = True,
    retry_on_permanent: bool = False,
    log_errors: bool = True
):
    """
    Decorator for applying error recovery to functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Factor for exponential backoff
        initial_delay: Initial delay between retries (seconds)
        fallback_value: Fallback value if all retries fail
        rollback_func: Function to call for rollback
        circuit_breaker_threshold: Number of failures before circuit breaker
        circuit_breaker_timeout: Time to keep circuit breaker open (seconds)
        retry_on_transient: Retry on transient errors
        retry_on_permanent: Retry on permanent errors
        log_errors: Whether to log errors
        
    Returns:
        Decorator function
        
    Example:
        @with_error_recovery(max_attempts=3, fallback_value={'status': 'failed'})
        def my_function(param1, param2):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Tuple[int, Any]:
            # Create recovery configuration
            config = RecoveryConfig(
                max_attempts=max_attempts,
                backoff_factor=backoff_factor,
                initial_delay=initial_delay,
                fallback_value=fallback_value,
                rollback_func=rollback_func,
                circuit_breaker_threshold=circuit_breaker_threshold,
                circuit_breaker_timeout=circuit_breaker_timeout,
                retry_on_transient=retry_on_transient,
                retry_on_permanent=retry_on_permanent,
                log_errors=log_errors
            )
            
            # Try to get logger from first argument (if it's a skill)
            logger = None
            if args and hasattr(args[0], 'logger'):
                logger = args[0].logger
            
            # Create recovery context
            context = ErrorRecoveryContext(config, logger)
            
            last_error = None
            
            # Retry loop
            for attempt in range(max_attempts):
                try:
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Record successful attempt
                    context.record_attempt(
                        strategy_type=RecoveryStrategyType.RETRY,
                        status=RecoveryStatus.SUCCESS,
                        recovery_time=0.0,
                        details={'attempt': attempt + 1}
                    )
                    
                    # Return success
                    return 0, result
                
                except Exception as e:
                    last_error = e
                    context.circuit_breaker_failures += 1
                    
                    # Record failed attempt
                    context.record_attempt(
                        strategy_type=RecoveryStrategyType.RETRY,
                        error=e,
                        status=RecoveryStatus.FAILED,
                        recovery_time=0.0,
                        details={'attempt': attempt + 1}
                    )
                    
                    # Check if should retry
                    if attempt < max_attempts - 1 and context.should_retry(e):
                        # Calculate backoff delay
                        delay = initial_delay * (backoff_factor ** attempt)
                        
                        if logger and log_errors:
                            logger.warning(
                                f"Function {func.__name__} failed, retrying in {delay}s",
                                extra={
                                    'attempt': attempt + 1,
                                    'max_attempts': max_attempts,
                                    'error': str(e),
                                    'delay': delay
                                }
                            )
                        
                        # Wait before retry
                        time.sleep(delay)
                    else:
                        # No more retries or should not retry
                        break
            
            # All retries failed
            context.trigger_circuit_breaker()
            
            # Try fallback strategy
            if fallback_value is not None:
                context.record_attempt(
                    strategy_type=RecoveryStrategyType.FALLBACK,
                    status=RecoveryStatus.SUCCESS,
                    details={'fallback_value': fallback_value}
                )
                
                if logger and log_errors:
                    logger.warning(
                        f"Function {func.__name__} failed after {max_attempts} attempts, using fallback",
                        extra={'error': str(last_error)}
                    )
                
                return 0, fallback_value
            
            # Try rollback strategy
            if rollback_func is not None:
                try:
                    rollback_func()
                    context.record_attempt(
                        strategy_type=RecoveryStrategyType.ROLLBACK,
                        status=RecoveryStatus.SUCCESS,
                        details={'rollback_performed': True}
                    )
                    
                    if logger and log_errors:
                        logger.info(
                            f"Rollback performed for {func.__name__}",
                            extra={'error': str(last_error)}
                        )
                except Exception as rollback_error:
                    context.record_attempt(
                        strategy_type=RecoveryStrategyType.ROLLBACK,
                        error=rollback_error,
                        status=RecoveryStatus.FAILED
                    )
                    
                    if logger and log_errors:
                        logger.error(
                            f"Rollback failed for {func.__name__}",
                            extra={'rollback_error': str(rollback_error)}
                        )
            
            # Return error
            if logger and log_errors:
                logger.error(
                    f"Function {func.__name__} failed after all recovery attempts",
                    extra={'error': str(last_error), 'attempts': len(context.attempts)}
                )
            
            if isinstance(last_error, IFlowError):
                return last_error.code.value, str(last_error)
            else:
                return ErrorCode.UNKNOWN_ERROR.value, str(last_error)
        
        return wrapper
    return decorator


def recover_with_strategy(
    strategies: List['RecoveryStrategyType'],
    config: Optional[RecoveryConfig] = None
):
    """
    Decorator for applying specific recovery strategies.
    
    Args:
        strategies: List of recovery strategies to apply
        config: Optional recovery configuration
        
    Returns:
        Decorator function
        
    Example:
        @recover_with_strategy([
            FallbackStrategy(default_value={'status': 'failed'}),
            RetryStrategy(max_attempts=3, backoff=exponential_backoff)
        ])
        def my_function(param1, param2):
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create default config if not provided
            if config is None:
                recovery_config = RecoveryConfig()
            else:
                recovery_config = config
            
            # Try to get logger from first argument (if it's a skill)
            logger = None
            if args and hasattr(args[0], 'logger'):
                logger = args[0].logger
            
            # Create recovery context
            context = ErrorRecoveryContext(recovery_config, logger)
            
            last_error = None
            
            # Try each strategy in order
            for strategy_type in strategies:
                try:
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Record success
                    context.record_attempt(
                        strategy_type=strategy_type,
                        status=RecoveryStatus.SUCCESS
                    )
                    
                    return 0, result
                
                except Exception as e:
                    last_error = e
                    context.circuit_breaker_failures += 1
                    
                    # Record failure
                    context.record_attempt(
                        strategy_type=strategy_type,
                        error=e,
                        status=RecoveryStatus.FAILED
                    )
                    
                    # Check if this strategy has more attempts
                    # (simplified - in real implementation would be more complex)
                    if recovery_config.max_attempts > 1:
                        # Retry with same strategy
                        continue
                    else:
                        # Move to next strategy
                        continue
            
            # All strategies failed
            if logger:
                logger.error(
                    f"Function {func.__name__} failed after all strategies",
                    extra={'error': str(last_error)}
                )
            
            if isinstance(last_error, IFlowError):
                return last_error.code.value, str(last_error)
            else:
                return ErrorCode.UNKNOWN_ERROR.value, str(last_error)
        
        return wrapper
    return decorator


def handle_transients(max_attempts: int = 3, backoff_factor: float = 2.0):
    """
    Convenience decorator for handling transient errors.
    
    Args:
        max_attempts: Maximum retry attempts
        backoff_factor: Backoff multiplier
        
    Returns:
        Decorator function
    """
    return with_error_recovery(
        max_attempts=max_attempts,
        backoff_factor=backoff_factor,
        retry_on_transient=True,
        retry_on_permanent=False
    )


def with_fallback(fallback_value: Any):
    """
    Convenience decorator for providing fallback value.
    
    Args:
        fallback_value: Value to return on failure
        
    Returns:
        Decorator function
    """
    return with_error_recovery(fallback_value=fallback_value)