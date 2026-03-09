"""Workflow State Machine.

This module provides a state machine pattern for managing workflow states,
phases, and branches with clear transition rules and guard conditions.
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime


class WorkflowState(Enum):
    """Workflow lifecycle states."""
    INITIALIZING = auto()
    REQUIREMENTS = auto()
    DESIGN = auto()
    IMPLEMENTATION = auto()
    TESTING = auto()
    DEPLOYMENT = auto()
    COMPLETE = auto()
    FAILED = auto()
    PAUSED = auto()


class BranchState(Enum):
    """Branch lifecycle states."""
    PENDING = auto()
    REVIEWING = auto()
    APPROVED = auto()
    MERGED = auto()
    UNAPPROVED = auto()
    NEEDS_CHANGES = auto()
    REJECTED = auto()
    REVERTED = auto()


class PhaseState(Enum):
    """Phase lifecycle states."""
    PENDING = auto()
    ACTIVE = auto()
    COMPLETE = auto()
    BLOCKED = auto()
    FAILED = auto()


class ReviewAction(Enum):
    """Review action types."""
    REQUEST_REVIEW = auto()
    APPROVE = auto()
    REQUEST_CHANGES = auto()
    UNAPPROVE = auto()
    MERGE = auto()
    REVERT = auto()


@dataclass
class StateTransition:
    """Represents a state transition."""
    from_state: Enum
    to_state: Enum
    action: str
    guard: Optional[Callable[[], bool]] = None
    on_enter: Optional[Callable[[], None]] = None
    on_exit: Optional[Callable[[], None]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StateChangeEvent:
    """Represents a state change event."""
    entity_type: str  # 'workflow', 'branch', 'phase'
    entity_id: str
    from_state: Optional[Enum]
    to_state: Enum
    action: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    actor: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowStateMachine:
    """
    State machine for workflow lifecycle management.
    
    Provides:
    - Defined state transitions
    - Guard conditions for transitions
    - Event tracking
    - State validation
    """
    
    # Define valid transitions
    TRANSITIONS: Dict[WorkflowState, List[StateTransition]] = {
        WorkflowState.INITIALIZING: [
            StateTransition(
                from_state=WorkflowState.INITIALIZING,
                to_state=WorkflowState.REQUIREMENTS,
                action='initialize_requirements',
                on_enter=lambda: print("Entering requirements phase")
            ),
            StateTransition(
                from_state=WorkflowState.INITIALIZING,
                to_state=WorkflowState.FAILED,
                action='fail_initialization'
            )
        ],
        WorkflowState.REQUIREMENTS: [
            StateTransition(
                from_state=WorkflowState.REQUIREMENTS,
                to_state=WorkflowState.DESIGN,
                action='complete_requirements',
                guard=lambda: True  # Would check requirements are complete
            ),
            StateTransition(
                from_state=WorkflowState.REQUIREMENTS,
                to_state=WorkflowState.FAILED,
                action='fail_requirements'
            ),
            StateTransition(
                from_state=WorkflowState.REQUIREMENTS,
                to_state=WorkflowState.PAUSED,
                action='pause'
            )
        ],
        WorkflowState.DESIGN: [
            StateTransition(
                from_state=WorkflowState.DESIGN,
                to_state=WorkflowState.IMPLEMENTATION,
                action='complete_design',
                guard=lambda: True  # Would check design is complete
            ),
            StateTransition(
                from_state=WorkflowState.DESIGN,
                to_state=WorkflowState.FAILED,
                action='fail_design'
            ),
            StateTransition(
                from_state=WorkflowState.DESIGN,
                to_state=WorkflowState.PAUSED,
                action='pause'
            )
        ],
        WorkflowState.IMPLEMENTATION: [
            StateTransition(
                from_state=WorkflowState.IMPLEMENTATION,
                to_state=WorkflowState.TESTING,
                action='complete_implementation',
                guard=lambda: True  # Would check implementation is complete
            ),
            StateTransition(
                from_state=WorkflowState.IMPLEMENTATION,
                to_state=WorkflowState.FAILED,
                action='fail_implementation'
            ),
            StateTransition(
                from_state=WorkflowState.IMPLEMENTATION,
                to_state=WorkflowState.PAUSED,
                action='pause'
            )
        ],
        WorkflowState.TESTING: [
            StateTransition(
                from_state=WorkflowState.TESTING,
                to_state=WorkflowState.DEPLOYMENT,
                action='complete_testing',
                guard=lambda: True  # Would check tests pass
            ),
            StateTransition(
                from_state=WorkflowState.TESTING,
                to_state=WorkflowState.IMPLEMENTATION,
                action='fail_testing_return_to_implementation'
            ),
            StateTransition(
                from_state=WorkflowState.TESTING,
                to_state=WorkflowState.FAILED,
                action='fail_testing'
            ),
            StateTransition(
                from_state=WorkflowState.TESTING,
                to_state=WorkflowState.PAUSED,
                action='pause'
            )
        ],
        WorkflowState.DEPLOYMENT: [
            StateTransition(
                from_state=WorkflowState.DEPLOYMENT,
                to_state=WorkflowState.COMPLETE,
                action='complete_deployment',
                guard=lambda: True  # Would check deployment successful
            ),
            StateTransition(
                from_state=WorkflowState.DEPLOYMENT,
                to_state=WorkflowState.IMPLEMENTATION,
                action='fail_deployment_return_to_implementation'
            ),
            StateTransition(
                from_state=WorkflowState.DEPLOYMENT,
                to_state=WorkflowState.FAILED,
                action='fail_deployment'
            ),
            StateTransition(
                from_state=WorkflowState.DEPLOYMENT,
                to_state=WorkflowState.PAUSED,
                action='pause'
            )
        ],
        WorkflowState.PAUSED: [
            StateTransition(
                from_state=WorkflowState.PAUSED,
                to_state=WorkflowState.REQUIREMENTS,
                action='resume_requirements',
                guard=lambda: True  # Would check if was in requirements
            ),
            StateTransition(
                from_state=WorkflowState.PAUSED,
                to_state=WorkflowState.DESIGN,
                action='resume_design',
                guard=lambda: True  # Would check if was in design
            ),
            StateTransition(
                from_state=WorkflowState.PAUSED,
                to_state=WorkflowState.IMPLEMENTATION,
                action='resume_implementation',
                guard=lambda: True  # Would check if was in implementation
            ),
            StateTransition(
                from_state=WorkflowState.PAUSED,
                to_state=WorkflowState.TESTING,
                action='resume_testing',
                guard=lambda: True  # Would check if was in testing
            ),
            StateTransition(
                from_state=WorkflowState.PAUSED,
                to_state=WorkflowState.DEPLOYMENT,
                action='resume_deployment',
                guard=lambda: True  # Would check if was in deployment
            ),
            StateTransition(
                from_state=WorkflowState.PAUSED,
                to_state=WorkflowState.FAILED,
                action='cancel'
            )
        ],
        WorkflowState.FAILED: [
            StateTransition(
                from_state=WorkflowState.FAILED,
                to_state=WorkflowState.INITIALIZING,
                action='restart'
            )
        ],
        WorkflowState.COMPLETE: [
            # Terminal state - no transitions
        ]
    }
    
    def __init__(self, workflow_id: str):
        """
        Initialize the state machine.
        
        Args:
            workflow_id: Unique identifier for the workflow
        """
        self.workflow_id = workflow_id
        self.current_state = WorkflowState.INITIALIZING
        self.previous_state: Optional[WorkflowState] = None
        self.event_history: List[StateChangeEvent] = []
        self.state_context: Dict[str, Any] = {}
        self._state_before_pause: Optional[WorkflowState] = None
    
    def can_transition(self, to_state: WorkflowState) -> bool:
        """
        Check if a transition to the target state is valid.
        
        Args:
            to_state: Target state
            
        Returns:
            True if transition is valid, False otherwise
        """
        transitions = self.TRANSITIONS.get(self.current_state, [])
        return any(t.to_state == to_state for t in transitions)
    
    def get_valid_transitions(self) -> List[StateTransition]:
        """
        Get all valid transitions from the current state.
        
        Returns:
            List of valid state transitions
        """
        return self.TRANSITIONS.get(self.current_state, [])
    
    def transition(
        self,
        to_state: WorkflowState,
        action: str,
        actor: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, Optional[str]]:
        """
        Perform a state transition.
        
        Args:
            to_state: Target state
            action: Action name
            actor: Optional actor performing the action
            reason: Optional reason for the transition
            **kwargs: Additional metadata
            
        Returns:
            Tuple of (success, error_message)
        """
        # Find matching transition
        transitions = self.TRANSITIONS.get(self.current_state, [])
        matching_transition = None
        
        for transition in transitions:
            if transition.to_state == to_state and transition.action == action:
                matching_transition = transition
                break
        
        if not matching_transition:
            return False, f"No valid transition from {self.current_state.name} to {to_state.name} with action '{action}'"
        
        # Check guard condition
        if matching_transition.guard and not matching_transition.guard():
            return False, f"Guard condition failed for transition to {to_state.name}"
        
        # Call on_exit handler
        if matching_transition.on_exit:
            matching_transition.on_exit()
        
        # Record state before pause if transitioning to paused
        if to_state == WorkflowState.PAUSED:
            self._state_before_pause = self.current_state
        
        # Store previous state
        self.previous_state = self.current_state
        
        # Update current state
        self.current_state = to_state
        
        # Update context
        self.state_context.update(kwargs)
        
        # Call on_enter handler
        if matching_transition.on_enter:
            matching_transition.on_enter()
        
        # Record event
        event = StateChangeEvent(
            entity_type='workflow',
            entity_id=self.workflow_id,
            from_state=self.previous_state,
            to_state=to_state,
            action=action,
            actor=actor,
            reason=reason,
            metadata=kwargs
        )
        self.event_history.append(event)
        
        return True, None
    
    def get_event_history(self, limit: Optional[int] = None) -> List[StateChangeEvent]:
        """
        Get event history.
        
        Args:
            limit: Optional limit on number of events to return
            
        Returns:
            List of state change events
        """
        if limit:
            return self.event_history[-limit:]
        return self.event_history
    
    def is_terminal(self) -> bool:
        """Check if current state is terminal (no outgoing transitions)."""
        return len(self.TRANSITIONS.get(self.current_state, [])) == 0
    
    def is_recoverable(self) -> bool:
        """Check if workflow can recover from current state."""
        if self.current_state == WorkflowState.COMPLETE:
            return False
        if self.current_state == WorkflowState.FAILED:
            return True  # Can restart
        return True


class BranchStateMachine:
    """
    State machine for branch lifecycle management.
    """
    
    # Define valid transitions for branches
    TRANSITIONS: Dict[BranchState, List[StateTransition]] = {
        BranchState.PENDING: [
            StateTransition(
                from_state=BranchState.PENDING,
                to_state=BranchState.REVIEWING,
                action='request_review'
            ),
            StateTransition(
                from_state=BranchState.PENDING,
                to_state=BranchState.REJECTED,
                action='reject'
            )
        ],
        BranchState.REVIEWING: [
            StateTransition(
                from_state=BranchState.REVIEWING,
                to_state=BranchState.APPROVED,
                action='approve',
                guard=lambda: True  # Would check review passed
            ),
            StateTransition(
                from_state=BranchState.REVIEWING,
                to_state=BranchState.NEEDS_CHANGES,
                action='request_changes'
            ),
            StateTransition(
                from_state=BranchState.REVIEWING,
                to_state=BranchState.REJECTED,
                action='reject'
            )
        ],
        BranchState.APPROVED: [
            StateTransition(
                from_state=BranchState.APPROVED,
                to_state=BranchState.MERGED,
                action='merge',
                guard=lambda: True  # Would check no conflicts
            ),
            StateTransition(
                from_state=BranchState.APPROVED,
                to_state=BranchState.UNAPPROVED,
                action='unapprove'
            )
        ],
        BranchState.UNAPPROVED: [
            StateTransition(
                from_state=BranchState.UNAPPROVED,
                to_state=BranchState.REVIEWING,
                action='request_review'
            ),
            StateTransition(
                from_state=BranchState.UNAPPROVED,
                to_state=BranchState.PENDING,
                action='return_to_pending'
            )
        ],
        BranchState.NEEDS_CHANGES: [
            StateTransition(
                from_state=BranchState.NEEDS_CHANGES,
                to_state=BranchState.REVIEWING,
                action='resubmit'
            )
        ],
        BranchState.MERGED: [
            StateTransition(
                from_state=BranchState.MERGED,
                to_state=BranchState.REVERTED,
                action='revert',
                guard=lambda: True  # Would check revert policy
            )
        ],
        BranchState.REJECTED: [
            StateTransition(
                from_state=BranchState.REJECTED,
                to_state=BranchState.PENDING,
                action='reopen'
            )
        ],
        BranchState.REVERTED: [
            # Terminal state
        ]
    }
    
    def __init__(self, branch_name: str, role: str):
        """
        Initialize the branch state machine.
        
        Args:
            branch_name: Name of the branch
            role: Role that owns the branch
        """
        self.branch_name = branch_name
        self.role = role
        self.current_state = BranchState.PENDING
        self.previous_state: Optional[BranchState] = None
        self.event_history: List[StateChangeEvent] = []
        self.state_context: Dict[str, Any] = {}
    
    def can_transition(self, to_state: BranchState) -> bool:
        """Check if transition is valid."""
        transitions = self.TRANSITIONS.get(self.current_state, [])
        return any(t.to_state == to_state for t in transitions)
    
    def transition(
        self,
        to_state: BranchState,
        action: str,
        actor: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, Optional[str]]:
        """Perform state transition."""
        transitions = self.TRANSITIONS.get(self.current_state, [])
        matching_transition = None
        
        for transition in transitions:
            if transition.to_state == to_state and transition.action == action:
                matching_transition = transition
                break
        
        if not matching_transition:
            return False, f"No valid transition from {self.current_state.name} to {to_state.name} with action '{action}'"
        
        if matching_transition.guard and not matching_transition.guard():
            return False, f"Guard condition failed for transition to {to_state.name}"
        
        if matching_transition.on_exit:
            matching_transition.on_exit()
        
        self.previous_state = self.current_state
        self.current_state = to_state
        self.state_context.update(kwargs)
        
        if matching_transition.on_enter:
            matching_transition.on_enter()
        
        event = StateChangeEvent(
            entity_type='branch',
            entity_id=self.branch_name,
            from_state=self.previous_state,
            to_state=to_state,
            action=action,
            actor=actor,
            reason=reason,
            metadata=kwargs
        )
        self.event_history.append(event)
        
        return True, None
    
    def is_mergeable(self) -> bool:
        """Check if branch is in a mergeable state."""
        return self.current_state == BranchState.APPROVED
    
    def can_be_reviewed(self) -> bool:
        """Check if branch can be reviewed."""
        return self.current_state == BranchState.REVIEWING
    
    def get_event_history(self, limit: Optional[int] = None) -> List[StateChangeEvent]:
        """Get event history."""
        if limit:
            return self.event_history[-limit:]
        return self.event_history


class PhaseStateMachine:
    """
    State machine for phase lifecycle management.
    """
    
    TRANSITIONS: Dict[PhaseState, List[StateTransition]] = {
        PhaseState.PENDING: [
            StateTransition(
                from_state=PhaseState.PENDING,
                to_state=PhaseState.ACTIVE,
                action='start',
                guard=lambda: True  # Would check dependencies satisfied
            ),
            StateTransition(
                from_state=PhaseState.PENDING,
                to_state=PhaseState.BLOCKED,
                action='block'
            )
        ],
        PhaseState.ACTIVE: [
            StateTransition(
                from_state=PhaseState.ACTIVE,
                to_state=PhaseState.COMPLETE,
                action='complete',
                guard=lambda: True  # Would check phase complete
            ),
            StateTransition(
                from_state=PhaseState.ACTIVE,
                to_state=PhaseState.FAILED,
                action='fail'
            ),
            StateTransition(
                from_state=PhaseState.ACTIVE,
                to_state=PhaseState.BLOCKED,
                action='block'
            )
        ],
        PhaseState.BLOCKED: [
            StateTransition(
                from_state=PhaseState.BLOCKED,
                to_state=PhaseState.PENDING,
                action='unblock'
            ),
            StateTransition(
                from_state=PhaseState.BLOCKED,
                to_state=PhaseState.ACTIVE,
                action='start',
                guard=lambda: True  # Would check dependencies satisfied
            )
        ],
        PhaseState.FAILED: [
            StateTransition(
                from_state=PhaseState.FAILED,
                to_state=PhaseState.PENDING,
                action='retry'
            )
        ],
        PhaseState.COMPLETE: [
            # Terminal state
        ]
    }
    
    def __init__(self, phase_name: str, role: str, order: int):
        """
        Initialize the phase state machine.
        
        Args:
            phase_name: Name of the phase
            role: Role responsible for the phase
            order: Phase order in workflow
        """
        self.phase_name = phase_name
        self.role = role
        self.order = order
        self.current_state = PhaseState.PENDING
        self.previous_state: Optional[PhaseState] = None
        self.event_history: List[StateChangeEvent] = []
        self.dependencies: List[int] = []
        self.state_context: Dict[str, Any] = {}
    
    def can_transition(self, to_state: PhaseState) -> bool:
        """Check if transition is valid."""
        transitions = self.TRANSITIONS.get(self.current_state, [])
        return any(t.to_state == to_state for t in transitions)
    
    def transition(
        self,
        to_state: PhaseState,
        action: str,
        actor: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs
    ) -> Tuple[bool, Optional[str]]:
        """Perform state transition."""
        transitions = self.TRANSITIONS.get(self.current_state, [])
        matching_transition = None
        
        for transition in transitions:
            if transition.to_state == to_state and transition.action == action:
                matching_transition = transition
                break
        
        if not matching_transition:
            return False, f"No valid transition from {self.current_state.name} to {to_state.name} with action '{action}'"
        
        if matching_transition.guard and not matching_transition.guard():
            return False, f"Guard condition failed for transition to {to_state.name}"
        
        if matching_transition.on_exit:
            matching_transition.on_exit()
        
        self.previous_state = self.current_state
        self.current_state = to_state
        self.state_context.update(kwargs)
        
        if matching_transition.on_enter:
            matching_transition.on_enter()
        
        event = StateChangeEvent(
            entity_type='phase',
            entity_id=self.phase_name,
            from_state=self.previous_state,
            to_state=to_state,
            action=action,
            actor=actor,
            reason=reason,
            metadata=kwargs
        )
        self.event_history.append(event)
        
        return True, None
    
    def add_dependency(self, phase_order: int):
        """Add a dependency on another phase."""
        if phase_order not in self.dependencies:
            self.dependencies.append(phase_order)
    
    def check_dependencies(self, phases: Dict[str, 'PhaseStateMachine']) -> bool:
        """
        Check if all dependencies are satisfied.
        
        Args:
            phases: Dictionary of all phases
            
        Returns:
            True if all dependencies satisfied, False otherwise
        """
        for dep_order in self.dependencies:
            for phase in phases.values():
                if phase.order == dep_order and phase.current_state != PhaseState.COMPLETE:
                    return False
        return True
    
    def get_event_history(self, limit: Optional[int] = None) -> List[StateChangeEvent]:
        """Get event history."""
        if limit:
            return self.event_history[-limit:]
        return self.event_history