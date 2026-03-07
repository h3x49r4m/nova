"""Workflow Parser - Parses workflow markdown files.

This module provides functionality to parse workflow definitions from
markdown files and extract structured step information.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any


class StepStatus(Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class WorkflowStatus(Enum):
    """Status of a workflow."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow."""
    step_number: int
    title: str
    description: str
    substeps: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_number": self.step_number,
            "title": self.title,
            "description": self.description,
            "substeps": self.substeps,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """Create from dictionary."""
        return cls(
            step_number=data["step_number"],
            title=data["title"],
            description=data["description"],
            substeps=data.get("substeps", []),
            status=StepStatus(data.get("status", "pending")),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            error=data.get("error"),
            notes=data.get("notes")
        )


@dataclass
class Workflow:
    """Represents a parsed workflow."""
    name: str
    objective: str
    steps: List[WorkflowStep] = field(default_factory=list)
    output: Optional[str] = None
    status: WorkflowStatus = WorkflowStatus.NOT_STARTED
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_step: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "objective": self.objective,
            "steps": [step.to_dict() for step in self.steps],
            "output": self.output,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "current_step": self.current_step,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workflow':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            objective=data["objective"],
            steps=[WorkflowStep.from_dict(s) for s in data.get("steps", [])],
            output=data.get("output"),
            status=WorkflowStatus(data.get("status", "not_started")),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            current_step=data.get("current_step", 0),
            metadata=data.get("metadata", {})
        )
    
    def get_progress(self) -> float:
        """Calculate workflow progress percentage."""
        if not self.steps:
            return 0.0
        
        completed = sum(1 for step in self.steps if step.status == StepStatus.COMPLETED)
        return (completed / len(self.steps)) * 100
    
    def get_next_step(self) -> Optional[WorkflowStep]:
        """Get the next step to execute."""
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                return step
        return None
    
    def get_step_by_number(self, step_number: int) -> Optional[WorkflowStep]:
        """Get a step by its number."""
        for step in self.steps:
            if step.step_number == step_number:
                return step
        return None


class WorkflowParser:
    """Parses workflow markdown files."""
    
    def __init__(self):
        """Initialize workflow parser."""
        self.step_pattern = re.compile(r'^(\d+)\.\s+\*\*(.+?)\*\*$')
        self.substep_pattern = re.compile(r'^\s+-\s+(.+)$')
    
    def parse(self, file_path: Path) -> Workflow:
        """
        Parse a workflow markdown file.
        
        Args:
            file_path: Path to the workflow markdown file
            
        Returns:
            Parsed Workflow object
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        return self.parse_content(content, file_path.stem)
    
    def parse_content(self, content: str, workflow_name: str) -> Workflow:
        """
        Parse workflow content from markdown text.
        
        Args:
            content: Markdown content
            workflow_name: Name of the workflow
            
        Returns:
            Parsed Workflow object
        """
        lines = content.split('\n')
        
        # Extract objective
        objective = self._extract_objective(lines)
        
        # Extract steps
        steps = self._extract_steps(lines)
        
        # Extract output
        output = self._extract_output(lines)
        
        return Workflow(
            name=workflow_name,
            objective=objective,
            steps=steps,
            output=output
        )
    
    def _extract_objective(self, lines: List[str]) -> str:
        """Extract objective from workflow lines."""
        for i, line in enumerate(lines):
            if line.startswith('## Objective'):
                if i + 1 < len(lines):
                    return lines[i + 1].strip()
        return ""
    
    def _extract_steps(self, lines: List[str]) -> List[WorkflowStep]:
        """Extract steps from workflow lines."""
        steps = []
        current_step = None
        in_steps_section = False
        
        for line in lines:
            # Check if we're in the steps section
            if line.startswith('## Steps'):
                in_steps_section = True
                continue
            
            # Check if we've left the steps section
            if in_steps_section and line.startswith('##') and not line.startswith('## Steps'):
                break
            
            # Parse step
            if in_steps_section:
                step_match = self.step_pattern.match(line)
                if step_match:
                    # Save previous step if exists
                    if current_step:
                        steps.append(current_step)
                    
                    # Create new step
                    step_number = int(step_match.group(1))
                    title = step_match.group(2)
                    current_step = WorkflowStep(
                        step_number=step_number,
                        title=title,
                        description=""
                    )
                    continue
                
                # Parse substep
                if current_step:
                    substep_match = self.substep_pattern.match(line)
                    if substep_match:
                        current_step.substeps.append(substep_match.group(1))
                    elif line.strip():
                        # Add to description
                        if current_step.description:
                            current_step.description += " " + line.strip()
                        else:
                            current_step.description = line.strip()
        
        # Add last step
        if current_step:
            steps.append(current_step)
        
        return steps
    
    def _extract_output(self, lines: List[str]) -> Optional[str]:
        """Extract output from workflow lines."""
        for i, line in enumerate(lines):
            if line.startswith('## Output'):
                if i + 1 < len(lines):
                    return lines[i + 1].strip()
        return None