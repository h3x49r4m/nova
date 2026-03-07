"""Error Recovery Strategies - Advanced recovery mechanisms for errors.

This module provides various error recovery strategies including fallbacks,
rollback, compensation, and custom recovery handlers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from .exceptions import IFlowError, ErrorCode, ErrorCategory

T = TypeVar('T')


class RecoveryStrategyType(Enum):
    """Types of recovery strategies."""
    RETRY = "retry"
    FALLBACK = "fallback"
    ROLLBACK = "rollback"
    COMPENSATION = "compensation"
    CIRCUIT_BREAKER = "circuit_breaker"
    CUSTOM = "custom"


class RecoveryStatus(Enum):
    """Status of recovery attempt."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RecoveryAttempt:
    """Record of a recovery attempt."""
    attempt_id: str
    strategy_type: RecoveryStrategyType
    timestamp: str
    status: RecoveryStatus = RecoveryStatus.PENDING
    error: Optional[Exception] = None
    recovery_time: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert attempt to dictionary."""
        return {
            "attempt_id": self.attempt_id,
            "strategy_type": self.strategy_type.value,
            "timestamp": self.timestamp,
            "status": self.status.value,
            "error": str(self.error) if self.error else None,
            "recovery_time": self.recovery_time,
            "details": self.details
        }


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""
    success: bool
    strategy_used: Optional[RecoveryStrategyType] = None
    attempts: List[RecoveryAttempt] = field(default_factory=list)
    final_value: Optional[Any] = None
    final_error: Optional[Exception] = None
    recovery_strategy_applied: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "strategy_used": self.strategy_used.value if self.strategy_used else None,
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "final_value": self.final_value,
            "final_error": str(self.final_error) if self.final_error else None,
            "recovery_strategy_applied": self.recovery_strategy_applied
        }


class RecoveryStrategy(ABC):
    """Base class for recovery strategies."""
    
    def __init__(self, strategy_type: RecoveryStrategyType):
        """
        Initialize recovery strategy.
        
        Args:
            strategy_type: Type of this recovery strategy
        """
        self.strategy_type = strategy_type
    
    @abstractmethod
    def can_recover(self, error: Exception) -> bool:
        """
        Determine if this strategy can recover from the error.
        
        Args:
            error: The error that occurred
            
        Returns:
            True if this strategy can recover
        """
        pass
    
    @abstractmethod
    def recover(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> RecoveryAttempt:
        """
        Attempt to recover from the error.
        
        Args:
            error: The error that occurred
            context: Context information for recovery
            
        Returns:
            RecoveryAttempt with recovery details
        """
        pass


class FallbackRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy that uses fallback values or functions."""
    
    def __init__(
        self,
        fallback_value: Optional[Any] = None,
        fallback_fn: Optional[Callable[..., Any]] = None,
        retryable_errors: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize fallback recovery strategy.
        
        Args:
            fallback_value: Value to use as fallback
            fallback_fn: Function to call for fallback value
            retryable_errors: List of error types to apply fallback to
        """
        super().__init__(RecoveryStrategyType.FALLBACK)
        self.fallback_value = fallback_value
        self.fallback_fn = fallback_fn
        self.retryable_errors = retryable_errors or []
    
    def can_recover(self, error: Exception) -> bool:
        """Check if fallback can be applied."""
        if not self.retryable_errors:
            return True  # Apply to all errors if no specific list
        
        for error_type in self.retryable_errors:
            if isinstance(error, error_type):
                return True
        return False
    
    def recover(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> RecoveryAttempt:
        """Attempt to recover using fallback."""
        import uuid
        
        attempt_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        start_time = datetime.now().timestamp()
        
        try:
            if self.fallback_fn:
                value = self.fallback_fn(**context.get("kwargs", {}))
            else:
                value = self.fallback_value
            
            recovery_time = datetime.now().timestamp() - start_time
            
            return RecoveryAttempt(
                attempt_id=attempt_id,
                strategy_type=self.strategy_type,
                timestamp=timestamp,
                status=RecoveryStatus.SUCCESS,
                recovery_time=recovery_time,
                details={"fallback_value": value}
            )
        except Exception as e:
            recovery_time = datetime.now().timestamp() - start_time
            
            return RecoveryAttempt(
                attempt_id=attempt_id,
                strategy_type=self.strategy_type,
                timestamp=timestamp,
                status=RecoveryStatus.FAILED,
                error=e,
                recovery_time=recovery_time
            )


class RollbackRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy that rolls back to a previous state."""
    
    def __init__(
        self,
        rollback_fn: Callable[..., None],
        retryable_errors: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize rollback recovery strategy.
        
        Args:
            rollback_fn: Function to call for rollback
            retryable_errors: List of error types to trigger rollback
        """
        super().__init__(RecoveryStrategyType.ROLLBACK)
        self.rollback_fn = rollback_fn
        self.retryable_errors = retryable_errors or []
    
    def can_recover(self, error: Exception) -> bool:
        """Check if rollback can be applied."""
        if not self.retryable_errors:
            return True
        
        for error_type in self.retryable_errors:
            if isinstance(error, error_type):
                return True
        return False
    
    def recover(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> RecoveryAttempt:
        """Attempt to recover using rollback."""
        import uuid
        
        attempt_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        start_time = datetime.now().timestamp()
        
        try:
            self.rollback_fn(**context.get("kwargs", {}))
            
            recovery_time = datetime.now().timestamp() - start_time
            
            return RecoveryAttempt(
                attempt_id=attempt_id,
                strategy_type=self.strategy_type,
                timestamp=timestamp,
                status=RecoveryStatus.SUCCESS,
                recovery_time=recovery_time,
                details={"rolled_back": True}
            )
        except Exception as e:
            recovery_time = datetime.now().timestamp() - start_time
            
            return RecoveryAttempt(
                attempt_id=attempt_id,
                strategy_type=self.strategy_type,
                timestamp=timestamp,
                status=RecoveryStatus.FAILED,
                error=e,
                recovery_time=recovery_time
            )


class CompensationRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy that applies compensation actions."""
    
    def __init__(
        self,
        compensation_actions: List[Callable[..., None]],
        retryable_errors: Optional[List[Type[Exception]]] = None
    ):
        """
        Initialize compensation recovery strategy.
        
        Args:
            compensation_actions: List of compensation actions to execute
            retryable_errors: List of error types to trigger compensation
        """
        super().__init__(RecoveryStrategyType.COMPENSATION)
        self.compensation_actions = compensation_actions
        self.retryable_errors = retryable_errors or []
    
    def can_recover(self, error: Exception) -> bool:
        """Check if compensation can be applied."""
        if not self.retryable_errors:
            return True
        
        for error_type in self.retryable_errors:
            if isinstance(error, error_type):
                return True
        return False
    
    def recover(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> RecoveryAttempt:
        """Attempt to recover using compensation."""
        import uuid
        
        attempt_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        start_time = datetime.now().timestamp()
        
        executed_actions = []
        failed_actions = []
        
        try:
            for action in self.compensation_actions:
                try:
                    action(**context.get("kwargs", {}))
                    executed_actions.append(action.__name__)
                except Exception as e:
                    failed_actions.append({
                        "action": action.__name__,
                        "error": str(e)
                    })
            
            recovery_time = datetime.now().timestamp() - start_time
            
            if failed_actions:
                return RecoveryAttempt(
                    attempt_id=attempt_id,
                    strategy_type=self.strategy_type,
                    timestamp=timestamp,
                    status=RecoveryStatus.FAILED,
                    error=Exception(f"Some compensation actions failed: {failed_actions}"),
                    recovery_time=recovery_time,
                    details={
                        "executed_actions": executed_actions,
                        "failed_actions": failed_actions
                    }
                )
            
            return RecoveryAttempt(
                attempt_id=attempt_id,
                strategy_type=self.strategy_type,
                timestamp=timestamp,
                status=RecoveryStatus.SUCCESS,
                recovery_time=recovery_time,
                details={
                    "executed_actions": executed_actions,
                    "total_actions": len(self.compensation_actions)
                }
            )
        except Exception as e:
            recovery_time = datetime.now().timestamp() - start_time
            
            return RecoveryAttempt(
                attempt_id=attempt_id,
                strategy_type=self.strategy_type,
                timestamp=timestamp,
                status=RecoveryStatus.FAILED,
                error=e,
                recovery_time=recovery_time
            )


class CustomRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy that uses custom recovery logic."""
    
    def __init__(
        self,
        recovery_fn: Callable[[Exception, Dict[str, Any]], Any],
        can_recover_fn: Optional[Callable[[Exception], bool]] = None
    ):
        """
        Initialize custom recovery strategy.
        
        Args:
            recovery_fn: Custom recovery function
            can_recover_fn: Optional function to determine if recovery is possible
        """
        super().__init__(RecoveryStrategyType.CUSTOM)
        self.recovery_fn = recovery_fn
        self.can_recover_fn = can_recover_fn
    
    def can_recover(self, error: Exception) -> bool:
        """Check if custom recovery can be applied."""
        if self.can_recover_fn:
            return self.can_recover_fn(error)
        return True
    
    def recover(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> RecoveryAttempt:
        """Attempt to recover using custom logic."""
        import uuid
        
        attempt_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        start_time = datetime.now().timestamp()
        
        try:
            result = self.recovery_fn(error, context)
            
            recovery_time = datetime.now().timestamp() - start_time
            
            return RecoveryAttempt(
                attempt_id=attempt_id,
                strategy_type=self.strategy_type,
                timestamp=timestamp,
                status=RecoveryStatus.SUCCESS,
                recovery_time=recovery_time,
                details={"result": result}
            )
        except Exception as e:
            recovery_time = datetime.now().timestamp() - start_time
            
            return RecoveryAttempt(
                attempt_id=attempt_id,
                strategy_type=self.strategy_type,
                timestamp=timestamp,
                status=RecoveryStatus.FAILED,
                error=e,
                recovery_time=recovery_time
            )


class ErrorRecoveryManager:
    """Manages error recovery strategies."""
    
    def __init__(self):
        """Initialize error recovery manager."""
        self.strategies: List[RecoveryStrategy] = []
        self.recovery_history: List[RecoveryResult] = []
    
    def add_strategy(self, strategy: RecoveryStrategy) -> None:
        """
        Add a recovery strategy.
        
        Args:
            strategy: Recovery strategy to add
        """
        self.strategies.append(strategy)
    
    def remove_strategy(self, strategy: RecoveryStrategy) -> None:
        """
        Remove a recovery strategy.
        
        Args:
            strategy: Recovery strategy to remove
        """
        if strategy in self.strategies:
            self.strategies.remove(strategy)
    
    def attempt_recovery(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> RecoveryResult:
        """
        Attempt to recover from an error using available strategies.
        
        Args:
            error: The error that occurred
            context: Context information for recovery
            
        Returns:
            RecoveryResult with recovery details
        """
        attempts = []
        
        for strategy in self.strategies:
            if not strategy.can_recover(error):
                continue
            
            attempt = strategy.recover(error, context)
            attempts.append(attempt)
            
            if attempt.status == RecoveryStatus.SUCCESS:
                # Recovery succeeded
                result = RecoveryResult(
                    success=True,
                    strategy_used=strategy.strategy_type,
                    attempts=attempts,
                    final_value=attempt.details.get("fallback_value"),
                    recovery_strategy_applied=strategy.__class__.__name__
                )
                self.recovery_history.append(result)
                return result
        
        # All recovery attempts failed
        result = RecoveryResult(
            success=False,
            attempts=attempts,
            final_error=error,
            recovery_strategy_applied="None"
        )
        self.recovery_history.append(result)
        return result
    
    def get_recovery_history(self, limit: int = 100) -> List[RecoveryResult]:
        """
        Get recovery history.
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of recovery results
        """
        return self.recovery_history[-limit:]
    
    def clear_history(self) -> None:
        """Clear recovery history."""
        self.recovery_history = []


def fallback(
    value: Optional[Any] = None,
    fn: Optional[Callable[..., Any]] = None,
    retryable_errors: Optional[List[Type[Exception]]] = None
):
    """
    Decorator to apply fallback recovery.
    
    Args:
        value: Fallback value
        fn: Fallback function
        retryable_errors: List of error types to apply fallback to
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                strategy = FallbackRecoveryStrategy(
                    fallback_value=value,
                    fallback_fn=fn,
                    retryable_errors=retryable_errors
                )
                
                # Only attempt recovery if the error is retryable
                if strategy.can_recover(e):
                    attempt = strategy.recover(e, {"kwargs": kwargs})
                    
                    if attempt.status == RecoveryStatus.SUCCESS:
                        return attempt.details.get("fallback_value")
                    else:
                        # Recovery failed, raise the recovery error
                        if attempt.error:
                            raise attempt.error
                        else:
                            raise
                else:
                    # Error is not retryable, raise it as-is
                    raise
        
        return wrapper
    return decorator


def recover_with(
    *strategies: RecoveryStrategy
):
    """
    Decorator to apply multiple recovery strategies.
    
    Args:
        *strategies: Recovery strategies to apply
        
    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                manager = ErrorRecoveryManager()
                for strategy in strategies:
                    manager.add_strategy(strategy)
                
                result = manager.attempt_recovery(e, {"kwargs": kwargs})
                
                if result.success and result.final_value is not None:
                    return result.final_value
                else:
                    raise
        
        return wrapper
    return decorator


# Common recovery scenarios

def create_fallback_strategy(
    fallback_value: Any,
    error_types: Optional[List[Type[Exception]]] = None
) -> FallbackRecoveryStrategy:
    """
    Create a fallback recovery strategy.
    
    Args:
        fallback_value: Value to use as fallback
        error_types: Error types to apply fallback to
        
    Returns:
        FallbackRecoveryStrategy instance
    """
    return FallbackRecoveryStrategy(
        fallback_value=fallback_value,
        retryable_errors=error_types
    )


def create_rollback_strategy(
    rollback_fn: Callable[..., None],
    error_types: Optional[List[Type[Exception]]] = None
) -> RollbackRecoveryStrategy:
    """
    Create a rollback recovery strategy.
    
    Args:
        rollback_fn: Function to call for rollback
        error_types: Error types to trigger rollback
        
    Returns:
        RollbackRecoveryStrategy instance
    """
    return RollbackRecoveryStrategy(
        rollback_fn=rollback_fn,
        retryable_errors=error_types
    )