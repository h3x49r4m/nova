"""Handoff Protocol - Manages formal handoffs between roles.

This module provides functionality for managing formal handoff protocols
between different roles in the development workflow, ensuring clear
communication and transfer of responsibility.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

from .exceptions import IFlowError, ErrorCode
from .structured_logger import StructuredLogger


class HandoffStatus(Enum):
    """Status of a handoff."""
    PENDING = "pending"
    INITIATED = "initiated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class HandoffPriority(Enum):
    """Priority levels for handoffs."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Role(Enum):
    """Available roles in the workflow."""
    CLIENT = "client"
    PRODUCT_MANAGER = "product_manager"
    TECH_LEAD = "tech_lead"
    SOFTWARE_ENGINEER = "software_engineer"
    TESTING_ENGINEER = "testing_engineer"
    QA_ENGINEER = "qa_engineer"
    SECURITY_ENGINEER = "security_engineer"
    DEVOPS_ENGINEER = "devops_engineer"
    DOCUMENTATION_SPECIALIST = "documentation_specialist"
    UI_UX_DESIGNER = "ui_ux_designer"


class HandoffRequirement:
    """Represents a requirement for a handoff."""
    
    def __init__(
        self,
        requirement_id: str,
        name: str,
        description: str,
        required: bool = True
    ):
        """
        Initialize a handoff requirement.
        
        Args:
            requirement_id: Unique identifier
            name: Human-readable name
            description: Description of the requirement
            required: Whether this requirement is mandatory
        """
        self.requirement_id = requirement_id
        self.name = name
        self.description = description
        self.required = required
        self.satisfied = False
        self.evidence: Optional[str] = None
        self.checked_at: Optional[str] = None
    
    def mark_satisfied(self, evidence: Optional[str] = None):
        """Mark the requirement as satisfied."""
        self.satisfied = True
        self.evidence = evidence
        self.checked_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert requirement to dictionary."""
        return {
            "requirement_id": self.requirement_id,
            "name": self.name,
            "description": self.description,
            "required": self.required,
            "satisfied": self.satisfied,
            "evidence": self.evidence,
            "checked_at": self.checked_at
        }


class Handoff:
    """Represents a handoff between roles."""
    
    def __init__(
        self,
        handoff_id: str,
        from_role: Role,
        to_role: Role,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a handoff.
        
        Args:
            handoff_id: Unique identifier for the handoff
            from_role: Role initiating the handoff
            to_role: Role receiving the handoff
            context: Additional context information
        """
        self.handoff_id = handoff_id
        self.from_role = from_role
        self.to_role = to_role
        self.context = context or {}
        self.status = HandoffStatus.PENDING
        self.priority = HandoffPriority.MEDIUM
        self.requirements: List[HandoffRequirement] = []
        self.artifacts: Dict[str, str] = {}
        self.notes: List[Dict[str, Any]] = []
        self.initiated_at: Optional[str] = None
        self.accepted_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.initiated_by: Optional[str] = None
        self.accepted_by: Optional[str] = None
        self.rejection_reason: Optional[str] = None
    
    def add_requirement(self, requirement: HandoffRequirement):
        """Add a requirement to the handoff."""
        self.requirements.append(requirement)
    
    def add_artifact(self, artifact_name: str, artifact_path: str):
        """Add an artifact to the handoff."""
        self.artifacts[artifact_name] = artifact_path
    
    def add_note(self, note: str, author: str):
        """Add a note to the handoff."""
        self.notes.append({
            "note": note,
            "author": author,
            "timestamp": datetime.now().isoformat()
        })
    
    def initiate(self, initiator: str):
        """Initiate the handoff."""
        self.status = HandoffStatus.INITIATED
        self.initiated_at = datetime.now().isoformat()
        self.initiated_by = initiator
    
    def accept(self, acceptor: str):
        """Accept the handoff."""
        self.status = HandoffStatus.ACCEPTED
        self.accepted_at = datetime.now().isoformat()
        self.accepted_by = acceptor
    
    def reject(self, rejector: str, reason: str):
        """Reject the handoff."""
        self.status = HandoffStatus.REJECTED
        self.rejection_reason = reason
        self.add_note(f"Rejected: {reason}", rejector)
    
    def complete(self):
        """Mark the handoff as completed."""
        self.status = HandoffStatus.COMPLETED
        self.completed_at = datetime.now().isoformat()
    
    def validate_requirements(self) -> Tuple[bool, List[str]]:
        """
        Validate that all required requirements are satisfied.
        
        Returns:
            Tuple of (is_valid, list_of_unsatisfied_requirements)
        """
        unsatisfied = []
        
        for req in self.requirements:
            if req.required and not req.satisfied:
                unsatisfied.append(req.name)
        
        return len(unsatisfied) == 0, unsatisfied
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert handoff to dictionary."""
        return {
            "handoff_id": self.handoff_id,
            "from_role": self.from_role.value,
            "to_role": self.to_role.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "context": self.context,
            "requirements": [req.to_dict() for req in self.requirements],
            "artifacts": self.artifacts,
            "notes": self.notes,
            "initiated_at": self.initiated_at,
            "accepted_at": self.accepted_at,
            "completed_at": self.completed_at,
            "initiated_by": self.initiated_by,
            "accepted_by": self.accepted_by,
            "rejection_reason": self.rejection_reason
        }


class HandoffProtocol:
    """Manages handoff protocols between roles."""
    
    def __init__(
        self,
        repo_root: Path,
        protocol_file: Optional[Path] = None
    ):
        """
        Initialize the handoff protocol manager.
        
        Args:
            repo_root: Repository root directory
            protocol_file: Path to protocol file
        """
        self.repo_root = repo_root
        self.protocol_dir = repo_root / ".iflow" / "handoffs"
        self.protocol_dir.mkdir(parents=True, exist_ok=True)
        self.protocol_file = protocol_file or (self.protocol_dir / "protocols.json")
        self.handoffs: Dict[str, Handoff] = {}
        self.logger = StructuredLogger(name="handoff-protocol")
        self._load_protocols()
    
    def _load_protocols(self):
        """Load handoff protocols from file."""
        if self.protocol_file.exists():
            try:
                with open(self.protocol_file, 'r') as f:
                    data = json.load(f)
                
                for handoff_data in data.get("handoffs", []):
                    handoff = self._deserialize_handoff(handoff_data)
                    if handoff:
                        self.handoffs[handoff.handoff_id] = handoff
            
            except (json.JSONDecodeError, IOError):
                pass
    
    def _save_protocols(self):
        """Save handoff protocols to file."""
        data = {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "handoffs": [handoff.to_dict() for handoff in self.handoffs.values()]
        }
        
        try:
            with open(self.protocol_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            raise IFlowError(
                f"Failed to save protocols: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def _deserialize_handoff(self, data: Dict[str, Any]) -> Optional[Handoff]:
        """Deserialize handoff from dictionary."""
        try:
            from_role = Role(data["from_role"])
            to_role = Role(data["to_role"])
            
            handoff = Handoff(
                handoff_id=data["handoff_id"],
                from_role=from_role,
                to_role=to_role,
                context=data.get("context", {})
            )
            
            handoff.status = HandoffStatus(data.get("status", "pending"))
            handoff.priority = HandoffPriority(data.get("priority", "medium"))
            handoff.artifacts = data.get("artifacts", {})
            handoff.notes = data.get("notes", [])
            handoff.initiated_at = data.get("initiated_at")
            handoff.accepted_at = data.get("accepted_at")
            handoff.completed_at = data.get("completed_at")
            handoff.initiated_by = data.get("initiated_by")
            handoff.accepted_by = data.get("accepted_by")
            handoff.rejection_reason = data.get("rejection_reason")
            
            # Deserialize requirements
            for req_data in data.get("requirements", []):
                req = HandoffRequirement(
                    requirement_id=req_data["requirement_id"],
                    name=req_data["name"],
                    description=req_data["description"],
                    required=req_data.get("required", True)
                )
                req.satisfied = req_data.get("satisfied", False)
                req.evidence = req_data.get("evidence")
                req.checked_at = req_data.get("checked_at")
                handoff.add_requirement(req)
            
            return handoff
        
        except (KeyError, ValueError) as e:
            self.logger.warning(f"Failed to deserialize handoff: {str(e)}")
            return None
    
    def _generate_handoff_id(self) -> str:
        """Generate a unique handoff ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"ho_{timestamp}"
    
    def create_handoff(
        self,
        from_role: Role,
        to_role: Role,
        context: Optional[Dict[str, Any]] = None,
        priority: HandoffPriority = HandoffPriority.MEDIUM
    ) -> Handoff:
        """
        Create a new handoff.
        
        Args:
            from_role: Role initiating the handoff
            to_role: Role receiving the handoff
            context: Additional context
            priority: Priority level
            
        Returns:
            Created Handoff object
        """
        handoff_id = self._generate_handoff_id()
        handoff = Handoff(
            handoff_id=handoff_id,
            from_role=from_role,
            to_role=to_role,
            context=context
        )
        handoff.priority = priority
        
        # Add default requirements based on role transition
        self._add_default_requirements(handoff)
        
        self.handoffs[handoff_id] = handoff
        self._save_protocols()
        
        self.logger.info(
            f"Created handoff: {handoff_id}",
            handoff_id=handoff_id,
            from_role=from_role.value,
            to_role=to_role.value
        )
        
        return handoff
    
    def _add_default_requirements(self, handoff: Handoff):
        """Add default requirements based on role transition."""
        transition = f"{handoff.from_role.value}_to_{handoff.to_role.value}"
        
        # Common requirements
        common_reqs = [
            HandoffRequirement(
                "code_reviewed",
                "Code Reviewed",
                "All code changes have been reviewed"
            ),
            HandoffRequirement(
                "tests_passing",
                "Tests Passing",
                "All tests are passing"
            ),
            HandoffRequirement(
                "documentation_updated",
                "Documentation Updated",
                "Documentation has been updated"
            )
        ]
        
        # Role-specific requirements
        role_specific_reqs = {
            "software_engineer_to_qa_engineer": [
                HandoffRequirement(
                    "test_plan_ready",
                    "Test Plan Ready",
                    "Test plan has been prepared"
                )
            ],
            "qa_engineer_to_software_engineer": [
                HandoffRequirement(
                    "bugs_reported",
                    "Bugs Reported",
                    "All bugs have been documented"
                )
            ],
            "tech_lead_to_devops_engineer": [
                HandoffRequirement(
                    "deployment_config",
                    "Deployment Configuration",
                    "Deployment configuration is ready"
                )
            ]
        }
        
        # Add common requirements
        for req in common_reqs:
            handoff.add_requirement(req)
        
        # Add role-specific requirements
        if transition in role_specific_reqs:
            for req in role_specific_reqs[transition]:
                handoff.add_requirement(req)
    
    def get_handoff(self, handoff_id: str) -> Optional[Handoff]:
        """Get a handoff by ID."""
        return self.handoffs.get(handoff_id)
    
    def list_handoffs(
        self,
        status: Optional[HandoffStatus] = None,
        from_role: Optional[Role] = None,
        to_role: Optional[Role] = None
    ) -> List[Handoff]:
        """
        List handoffs with optional filtering.
        
        Args:
            status: Optional status filter
            from_role: Optional from_role filter
            to_role: Optional to_role filter
            
        Returns:
            List of matching handoffs
        """
        handoffs = list(self.handoffs.values())
        
        if status:
            handoffs = [h for h in handoffs if h.status == status]
        
        if from_role:
            handoffs = [h for h in handoffs if h.from_role == from_role]
        
        if to_role:
            handoffs = [h for h in handoffs if h.to_role == to_role]
        
        return handoffs
    
    def initiate_handoff(self, handoff_id: str, initiator: str):
        """Initiate a handoff."""
        handoff = self.get_handoff(handoff_id)
        if not handoff:
            raise IFlowError(
                f"Handoff '{handoff_id}' not found",
                ErrorCode.NOT_FOUND
            )
        
        # Validate requirements before initiating
        is_valid, unsatisfied = handoff.validate_requirements()
        if not is_valid:
            raise IFlowError(
                f"Cannot initiate handoff: unsatisfied requirements: {', '.join(unsatisfied)}",
                ErrorCode.VALIDATION_ERROR
            )
        
        handoff.initiate(initiator)
        self._save_protocols()
        
        self.logger.info(
            f"Initiated handoff: {handoff_id}",
            handoff_id=handoff_id,
            initiator=initiator
        )
    
    def accept_handoff(self, handoff_id: str, acceptor: str):
        """Accept a handoff."""
        handoff = self.get_handoff(handoff_id)
        if not handoff:
            raise IFlowError(
                f"Handoff '{handoff_id}' not found",
                ErrorCode.NOT_FOUND
            )
        
        if handoff.status != HandoffStatus.INITIATED:
            raise IFlowError(
                f"Cannot accept handoff in status: {handoff.status.value}",
                ErrorCode.INVALID_STATE
            )
        
        handoff.accept(acceptor)
        self._save_protocols()
        
        self.logger.info(
            f"Accepted handoff: {handoff_id}",
            handoff_id=handoff_id,
            acceptor=acceptor
        )
    
    def reject_handoff(self, handoff_id: str, rejector: str, reason: str):
        """Reject a handoff."""
        handoff = self.get_handoff(handoff_id)
        if not handoff:
            raise IFlowError(
                f"Handoff '{handoff_id}' not found",
                ErrorCode.NOT_FOUND
            )
        
        handoff.reject(rejector, reason)
        self._save_protocols()
        
        self.logger.warning(
            f"Rejected handoff: {handoff_id}",
            handoff_id=handoff_id,
            rejector=rejector,
            reason=reason
        )
    
    def complete_handoff(self, handoff_id: str):
        """Mark a handoff as completed."""
        handoff = self.get_handoff(handoff_id)
        if not handoff:
            raise IFlowError(
                f"Handoff '{handoff_id}' not found",
                ErrorCode.NOT_FOUND
            )
        
        if handoff.status != HandoffStatus.ACCEPTED:
            raise IFlowError(
                f"Cannot complete handoff in status: {handoff.status.value}",
                ErrorCode.INVALID_STATE
            )
        
        handoff.complete()
        self._save_protocols()
        
        self.logger.info(
            f"Completed handoff: {handoff_id}",
            handoff_id=handoff_id
        )
    
    def update_requirement(
        self,
        handoff_id: str,
        requirement_id: str,
        satisfied: bool,
        evidence: Optional[str] = None
    ):
        """Update a requirement status."""
        handoff = self.get_handoff(handoff_id)
        if not handoff:
            raise IFlowError(
                f"Handoff '{handoff_id}' not found",
                ErrorCode.NOT_FOUND
            )
        
        for req in handoff.requirements:
            if req.requirement_id == requirement_id:
                if satisfied:
                    req.mark_satisfied(evidence)
                else:
                    req.satisfied = False
                    req.evidence = None
                    req.checked_at = None
                
                self._save_protocols()
                return
        
        raise IFlowError(
            f"Requirement '{requirement_id}' not found",
            ErrorCode.NOT_FOUND
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get handoff statistics."""
        status_counts = {}
        role_transition_counts = {}
        
        for handoff in self.handoffs.values():
            status = handoff.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            transition = f"{handoff.from_role.value}_to_{handoff.to_role.value}"
            role_transition_counts[transition] = role_transition_counts.get(transition, 0) + 1
        
        return {
            "total_handoffs": len(self.handoffs),
            "status_counts": status_counts,
            "role_transitions": role_transition_counts
        }


def create_handoff_protocol(
    repo_root: Path,
    protocol_file: Optional[Path] = None
) -> HandoffProtocol:
    """Create a handoff protocol instance."""
    return HandoffProtocol(repo_root, protocol_file)