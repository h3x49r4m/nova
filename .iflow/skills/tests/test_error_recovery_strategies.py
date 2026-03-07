"""Tests for error recovery strategies."""

from unittest.mock import Mock, MagicMock

import pytest

from utils.error_recovery_strategies import (
    RecoveryStrategyType,
    RecoveryStatus,
    RecoveryAttempt,
    RecoveryResult,
    FallbackRecoveryStrategy,
    RollbackRecoveryStrategy,
    CompensationRecoveryStrategy,
    CustomRecoveryStrategy,
    ErrorRecoveryManager,
    fallback,
    recover_with,
    create_fallback_strategy,
    create_rollback_strategy
)
from utils.exceptions import IFlowError, ErrorCode


class TestRecoveryStrategyType:
    """Test RecoveryStrategyType enum."""
    
    def test_types(self):
        """Test all recovery strategy types exist."""
        assert RecoveryStrategyType.RETRY.value == "retry"
        assert RecoveryStrategyType.FALLBACK.value == "fallback"
        assert RecoveryStrategyType.ROLLBACK.value == "rollback"
        assert RecoveryStrategyType.COMPENSATION.value == "compensation"
        assert RecoveryStrategyType.CIRCUIT_BREAKER.value == "circuit_breaker"
        assert RecoveryStrategyType.CUSTOM.value == "custom"


class TestRecoveryStatus:
    """Test RecoveryStatus enum."""
    
    def test_statuses(self):
        """Test all recovery statuses exist."""
        assert RecoveryStatus.PENDING.value == "pending"
        assert RecoveryStatus.IN_PROGRESS.value == "in_progress"
        assert RecoveryStatus.SUCCESS.value == "success"
        assert RecoveryStatus.FAILED.value == "failed"
        assert RecoveryStatus.SKIPPED.value == "skipped"


class TestRecoveryAttempt:
    """Test RecoveryAttempt dataclass."""
    
    def test_attempt_creation(self):
        """Test creating recovery attempt."""
        attempt = RecoveryAttempt(
            attempt_id="a1",
            strategy_type=RecoveryStrategyType.FALLBACK,
            timestamp="2024-01-01T00:00:00",
            status=RecoveryStatus.SUCCESS
        )
        
        assert attempt.attempt_id == "a1"
        assert attempt.strategy_type == RecoveryStrategyType.FALLBACK
        assert attempt.status == RecoveryStatus.SUCCESS
    
    def test_attempt_to_dict(self):
        """Test converting attempt to dictionary."""
        error = Exception("Test error")
        attempt = RecoveryAttempt(
            attempt_id="a1",
            strategy_type=RecoveryStrategyType.FALLBACK,
            timestamp="2024-01-01T00:00:00",
            status=RecoveryStatus.FAILED,
            error=error,
            recovery_time=1.5
        )
        
        data = attempt.to_dict()
        
        assert data["attempt_id"] == "a1"
        assert data["strategy_type"] == "fallback"
        assert data["status"] == "failed"
        assert data["error"] == "Test error"
        assert data["recovery_time"] == 1.5


class TestRecoveryResult:
    """Test RecoveryResult dataclass."""
    
    def test_result_creation(self):
        """Test creating recovery result."""
        result = RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategyType.FALLBACK,
            final_value="fallback_value"
        )
        
        assert result.success is True
        assert result.strategy_used == RecoveryStrategyType.FALLBACK
        assert result.final_value == "fallback_value"
    
    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        error = Exception("Test error")
        attempt = RecoveryAttempt(
            attempt_id="a1",
            strategy_type=RecoveryStrategyType.FALLBACK,
            timestamp="2024-01-01T00:00:00"
        )
        
        result = RecoveryResult(
            success=False,
            attempts=[attempt],
            final_error=error
        )
        
        data = result.to_dict()
        
        assert data["success"] is False
        assert len(data["attempts"]) == 1
        assert data["final_error"] == "Test error"


class TestFallbackRecoveryStrategy:
    """Test FallbackRecoveryStrategy."""
    
    def test_can_recover_all_errors(self):
        """Test can_recover with no specific error types."""
        strategy = FallbackRecoveryStrategy(fallback_value="default")
        
        assert strategy.can_recover(ValueError("Error")) is True
        assert strategy.can_recover(TypeError("Error")) is True
    
    def test_can_recover_specific_errors(self):
        """Test can_recover with specific error types."""
        strategy = FallbackRecoveryStrategy(
            fallback_value="default",
            retryable_errors=[ValueError]
        )
        
        assert strategy.can_recover(ValueError("Error")) is True
        assert strategy.can_recover(TypeError("Error")) is False
    
    def test_recover_with_value(self):
        """Test recover with fallback value."""
        strategy = FallbackRecoveryStrategy(fallback_value="default")
        
        attempt = strategy.recover(ValueError("Error"), {})
        
        assert attempt.status == RecoveryStatus.SUCCESS
        assert attempt.details["fallback_value"] == "default"
    
    def test_recover_with_function(self):
        """Test recover with fallback function."""
        def get_default():
            return "computed_default"
        
        strategy = FallbackRecoveryStrategy(fallback_fn=get_default)
        
        attempt = strategy.recover(ValueError("Error"), {})
        
        assert attempt.status == RecoveryStatus.SUCCESS
        assert attempt.details["fallback_value"] == "computed_default"
    
    def test_recover_with_function_args(self):
        """Test recover with fallback function that uses context."""
        def get_default(name):
            return f"Hello, {name}!"
        
        strategy = FallbackRecoveryStrategy(fallback_fn=get_default)
        
        attempt = strategy.recover(
            ValueError("Error"),
            {"kwargs": {"name": "World"}}
        )
        
        assert attempt.status == RecoveryStatus.SUCCESS
        assert attempt.details["fallback_value"] == "Hello, World!"
    
    def test_recover_function_fails(self):
        """Test recover when fallback function fails."""
        def failing_fallback():
            raise RuntimeError("Fallback failed")
        
        strategy = FallbackRecoveryStrategy(fallback_fn=failing_fallback)
        
        attempt = strategy.recover(ValueError("Error"), {})
        
        assert attempt.status == RecoveryStatus.FAILED
        assert attempt.error is not None
        assert isinstance(attempt.error, RuntimeError)


class TestRollbackRecoveryStrategy:
    """Test RollbackRecoveryStrategy."""
    
    def test_can_recover_all_errors(self):
        """Test can_recover with no specific error types."""
        rollback_fn = Mock()
        strategy = RollbackRecoveryStrategy(rollback_fn=rollback_fn)
        
        assert strategy.can_recover(ValueError("Error")) is True
    
    def test_can_recover_specific_errors(self):
        """Test can_recover with specific error types."""
        rollback_fn = Mock()
        strategy = RollbackRecoveryStrategy(
            rollback_fn=rollback_fn,
            retryable_errors=[ValueError]
        )
        
        assert strategy.can_recover(ValueError("Error")) is True
        assert strategy.can_recover(TypeError("Error")) is False
    
    def test_recover_success(self):
        """Test successful rollback."""
        rollback_fn = Mock()
        strategy = RollbackRecoveryStrategy(rollback_fn=rollback_fn)
        
        attempt = strategy.recover(ValueError("Error"), {})
        
        assert attempt.status == RecoveryStatus.SUCCESS
        assert attempt.details["rolled_back"] is True
        rollback_fn.assert_called_once()
    
    def test_recover_with_args(self):
        """Test rollback with arguments."""
        rollback_fn = Mock()
        strategy = RollbackRecoveryStrategy(rollback_fn=rollback_fn)
        
        attempt = strategy.recover(
            ValueError("Error"),
            {"kwargs": {"resource_id": "123"}}
        )
        
        assert attempt.status == RecoveryStatus.SUCCESS
        rollback_fn.assert_called_once_with(resource_id="123")
    
    def test_recover_failure(self):
        """Test rollback when rollback function fails."""
        def failing_rollback():
            raise RuntimeError("Rollback failed")
        
        strategy = RollbackRecoveryStrategy(rollback_fn=failing_rollback)
        
        attempt = strategy.recover(ValueError("Error"), {})
        
        assert attempt.status == RecoveryStatus.FAILED
        assert attempt.error is not None


class TestCompensationRecoveryStrategy:
    """Test CompensationRecoveryStrategy."""
    
    def test_can_recover_all_errors(self):
        """Test can_recover with no specific error types."""
        actions = [Mock(), Mock()]
        strategy = CompensationRecoveryStrategy(compensation_actions=actions)
        
        assert strategy.can_recover(ValueError("Error")) is True
    
    def test_recover_success(self):
        """Test successful compensation."""
        action1 = Mock(__name__="action1")
        action2 = Mock(__name__="action2")
        strategy = CompensationRecoveryStrategy(
            compensation_actions=[action1, action2]
        )
        
        attempt = strategy.recover(ValueError("Error"), {})
        
        assert attempt.status == RecoveryStatus.SUCCESS
        assert attempt.details["executed_actions"] == ["action1", "action2"]
        assert attempt.details["total_actions"] == 2
        action1.assert_called_once()
        action2.assert_called_once()
    
    def test_recover_partial_failure(self):
        """Test compensation with some actions failing."""
        def failing_action():
            raise RuntimeError("Action failed")
        
        action1 = Mock(__name__="action1")
        action2 = Mock(__name__="action2", side_effect=failing_action)
        
        strategy = CompensationRecoveryStrategy(
            compensation_actions=[action1, action2]
        )
        
        attempt = strategy.recover(ValueError("Error"), {})
        
        assert attempt.status == RecoveryStatus.FAILED
        assert len(attempt.details["failed_actions"]) == 1
        assert attempt.details["executed_actions"] == ["action1"]
    
    def test_recover_all_failures(self):
        """Test compensation with all actions failing."""
        def failing_action():
            raise RuntimeError("Action failed")
        
        action1 = Mock(__name__="failing_action1", side_effect=failing_action)
        action2 = Mock(__name__="failing_action2", side_effect=failing_action)
        
        strategy = CompensationRecoveryStrategy(
            compensation_actions=[action1, action2]
        )
        
        attempt = strategy.recover(ValueError("Error"), {})
        
        assert attempt.status == RecoveryStatus.FAILED
        assert len(attempt.details["failed_actions"]) == 2


class TestCustomRecoveryStrategy:
    """Test CustomRecoveryStrategy."""
    
    def test_can_recover_default(self):
        """Test can_recover with default behavior."""
        def recovery_fn(error, context):
            return "recovered"
        
        strategy = CustomRecoveryStrategy(recovery_fn=recovery_fn)
        
        assert strategy.can_recover(ValueError("Error")) is True
    
    def test_can_recover_custom(self):
        """Test can_recover with custom function."""
        def recovery_fn(error, context):
            return "recovered"
        
        def can_recover_fn(error):
            return isinstance(error, ValueError)
        
        strategy = CustomRecoveryStrategy(
            recovery_fn=recovery_fn,
            can_recover_fn=can_recover_fn
        )
        
        assert strategy.can_recover(ValueError("Error")) is True
        assert strategy.can_recover(TypeError("Error")) is False
    
    def test_recover_success(self):
        """Test successful custom recovery."""
        def recovery_fn(error, context):
            return "recovered"
        
        strategy = CustomRecoveryStrategy(recovery_fn=recovery_fn)
        
        attempt = strategy.recover(ValueError("Error"), {})
        
        assert attempt.status == RecoveryStatus.SUCCESS
        assert attempt.details["result"] == "recovered"
    
    def test_recover_failure(self):
        """Test custom recovery that fails."""
        def failing_recovery(error, context):
            raise RuntimeError("Recovery failed")
        
        strategy = CustomRecoveryStrategy(recovery_fn=failing_recovery)
        
        attempt = strategy.recover(ValueError("Error"), {})
        
        assert attempt.status == RecoveryStatus.FAILED
        assert attempt.error is not None


class TestErrorRecoveryManager:
    """Test ErrorRecoveryManager."""
    
    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = ErrorRecoveryManager()
        
        assert manager.strategies == []
        assert manager.recovery_history == []
    
    def test_add_strategy(self):
        """Test adding a strategy."""
        manager = ErrorRecoveryManager()
        strategy = FallbackRecoveryStrategy(fallback_value="default")
        
        manager.add_strategy(strategy)
        
        assert len(manager.strategies) == 1
        assert manager.strategies[0] == strategy
    
    def test_remove_strategy(self):
        """Test removing a strategy."""
        manager = ErrorRecoveryManager()
        strategy = FallbackRecoveryStrategy(fallback_value="default")
        
        manager.add_strategy(strategy)
        manager.remove_strategy(strategy)
        
        assert len(manager.strategies) == 0
    
    def test_attempt_recovery_success(self):
        """Test successful recovery attempt."""
        manager = ErrorRecoveryManager()
        strategy = FallbackRecoveryStrategy(fallback_value="default")
        manager.add_strategy(strategy)
        
        result = manager.attempt_recovery(ValueError("Error"), {})
        
        assert result.success is True
        assert result.strategy_used == RecoveryStrategyType.FALLBACK
        assert result.final_value == "default"
    
    def test_attempt_recovery_multiple_strategies(self):
        """Test recovery with multiple strategies."""
        manager = ErrorRecoveryManager()
        
        # First strategy should succeed
        strategy1 = FallbackRecoveryStrategy(fallback_value="default1")
        strategy2 = FallbackRecoveryStrategy(fallback_value="default2")
        
        manager.add_strategy(strategy1)
        manager.add_strategy(strategy2)
        
        result = manager.attempt_recovery(ValueError("Error"), {})
        
        assert result.success is True
        assert result.final_value == "default1"
        assert len(result.attempts) == 1
    
    def test_attempt_recovery_skip_inapplicable(self):
        """Test recovery skips strategies that can't recover."""
        manager = ErrorRecoveryManager()
        
        # Only retry ValueError
        strategy = FallbackRecoveryStrategy(
            fallback_value="default",
            retryable_errors=[ValueError]
        )
        manager.add_strategy(strategy)
        
        result = manager.attempt_recovery(TypeError("Error"), {})
        
        assert result.success is False
        assert len(result.attempts) == 0
    
    def test_attempt_recovery_all_fail(self):
        """Test recovery when all strategies fail."""
        manager = ErrorRecoveryManager()
        
        def failing_fallback():
            raise RuntimeError("Fallback failed")
        
        strategy = FallbackRecoveryStrategy(fallback_fn=failing_fallback)
        manager.add_strategy(strategy)
        
        result = manager.attempt_recovery(ValueError("Error"), {})
        
        assert result.success is False
        assert len(result.attempts) == 1
        assert result.final_error is not None
    
    def test_get_recovery_history(self):
        """Test getting recovery history."""
        manager = ErrorRecoveryManager()
        strategy = FallbackRecoveryStrategy(fallback_value="default")
        manager.add_strategy(strategy)
        
        manager.attempt_recovery(ValueError("Error"), {})
        manager.attempt_recovery(ValueError("Error"), {})
        manager.attempt_recovery(ValueError("Error"), {})
        
        history = manager.get_recovery_history()
        
        assert len(history) == 3
    
    def test_get_recovery_history_limit(self):
        """Test getting recovery history with limit."""
        manager = ErrorRecoveryManager()
        strategy = FallbackRecoveryStrategy(fallback_value="default")
        manager.add_strategy(strategy)
        
        for _ in range(5):
            manager.attempt_recovery(ValueError("Error"), {})
        
        history = manager.get_recovery_history(limit=3)
        
        assert len(history) == 3
    
    def test_clear_history(self):
        """Test clearing recovery history."""
        manager = ErrorRecoveryManager()
        strategy = FallbackRecoveryStrategy(fallback_value="default")
        manager.add_strategy(strategy)
        
        manager.attempt_recovery(ValueError("Error"), {})
        manager.clear_history()
        
        assert len(manager.recovery_history) == 0


class TestFallbackDecorator:
    """Test fallback decorator."""
    
    def test_fallback_decorator_success(self):
        """Test fallback decorator when function succeeds."""
        @fallback(value="default")
        def success_fn():
            return "success"
        
        result = success_fn()
        
        assert result == "success"
    
    def test_fallback_decorator_fallback(self):
        """Test fallback decorator when function fails."""
        @fallback(value="default")
        def failing_fn():
            raise ValueError("Error")
        
        result = failing_fn()
        
        assert result == "default"
    
    def test_fallback_decorator_specific_error(self):
        """Test fallback decorator with specific error type."""
        @fallback(value="default", retryable_errors=[ValueError])
        def failing_fn():
            raise TypeError("Error")
        
        with pytest.raises(TypeError):
            failing_fn()
    
    def test_fallback_decorator_with_function(self):
        """Test fallback decorator with fallback function."""
        def get_default():
            return "computed_default"
        
        @fallback(fn=get_default)
        def failing_fn():
            raise ValueError("Error")
        
        result = failing_fn()
        
        assert result == "computed_default"
    
    def test_fallback_decorator_fallback_fails(self):
        """Test fallback decorator when fallback fails."""
        def failing_fallback():
            raise RuntimeError("Fallback failed")
        
        @fallback(fn=failing_fallback)
        def failing_fn():
            raise ValueError("Error")
        
        with pytest.raises(RuntimeError):
            failing_fn()


class TestRecoverWithDecorator:
    """Test recover_with decorator."""
    
    def test_recover_with_decorator_success(self):
        """Test recover_with decorator when function succeeds."""
        strategy = FallbackRecoveryStrategy(fallback_value="default")
        
        @recover_with(strategy)
        def success_fn():
            return "success"
        
        result = success_fn()
        
        assert result == "success"
    
    def test_recover_with_decorator_recovery(self):
        """Test recover_with decorator when recovery succeeds."""
        strategy = FallbackRecoveryStrategy(fallback_value="default")
        
        @recover_with(strategy)
        def failing_fn():
            raise ValueError("Error")
        
        result = failing_fn()
        
        assert result == "default"
    
    def test_recover_with_decorator_multiple_strategies(self):
        """Test recover_with decorator with multiple strategies."""
        strategy1 = FallbackRecoveryStrategy(fallback_value="default1")
        strategy2 = FallbackRecoveryStrategy(fallback_value="default2")
        
        @recover_with(strategy1, strategy2)
        def failing_fn():
            raise ValueError("Error")
        
        result = failing_fn()
        
        # Should use first strategy that succeeds
        assert result == "default1"


class TestCreateStrategies:
    """Test strategy factory functions."""
    
    def test_create_fallback_strategy(self):
        """Test creating fallback strategy."""
        strategy = create_fallback_strategy("default", [ValueError])
        
        assert isinstance(strategy, FallbackRecoveryStrategy)
        assert strategy.fallback_value == "default"
        assert strategy.retryable_errors == [ValueError]
    
    def test_create_rollback_strategy(self):
        """Test creating rollback strategy."""
        rollback_fn = Mock()
        strategy = create_rollback_strategy(rollback_fn, [ValueError])
        
        assert isinstance(strategy, RollbackRecoveryStrategy)
        assert strategy.rollback_fn == rollback_fn
        assert strategy.retryable_errors == [ValueError]