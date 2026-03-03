"""Progress Indicator - Visual progress tracking for long-running operations.

This module provides functionality for displaying progress indicators
and status updates during long-running operations.
"""

import sys
import time
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass


class ProgressStyle(Enum):
    """Styles of progress indicators."""
    BAR = "bar"
    DOTS = "dots"
    SPINNER = "spinner"
    PERCENTAGE = "percentage"
    COUNTER = "counter"


class ProgressStatus(Enum):
    """Status of progress operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressStep:
    """Represents a single step in a multi-step operation."""
    name: str
    total: int = 100
    completed: int = 0
    status: ProgressStatus = ProgressStatus.PENDING
    message: str = ""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total == 0:
            return 100.0
        return (self.completed / self.total) * 100
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if not self.start_time:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def estimated_remaining(self) -> float:
        """Estimate remaining time in seconds."""
        if not self.start_time or self.completed == 0:
            return 0.0
        elapsed = self.elapsed_time
        rate = self.completed / elapsed
        if rate == 0:
            return 0.0
        remaining = self.total - self.completed
        return remaining / rate


class ProgressIndicator:
    """Visual progress indicator for long-running operations."""
    
    SPINNERS = [
        ["|", "/", "-", "\\"],
        ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        ["⣾", "⣽", "⣻", "⢿"],
        ["⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈"]
    ]
    
    def __init__(
        self,
        total: int = 100,
        description: str = "",
        style: ProgressStyle = ProgressStyle.BAR,
        show_time: bool = True,
        show_eta: bool = True,
        width: int = 50
    ):
        """
        Initialize the progress indicator.
        
        Args:
            total: Total number of items/operations
            description: Description of the operation
            style: Style of progress indicator
            show_time: Whether to show elapsed time
            show_eta: Whether to show estimated time remaining
            width: Width of progress bar (for BAR style)
        """
        self.total = total
        self.current = 0
        self.description = description
        self.style = style
        self.show_time = show_time
        self.show_eta = show_eta
        self.width = width
        self.start_time: Optional[float] = None
        self.last_update: Optional[float] = None
        self.spinner_index = 0
        self.spinner_style = 1  # Default spinner style
        
        self.steps: List[ProgressStep] = []
        self.current_step_index = 0
    
    def start(self):
        """Start the progress indicator."""
        self.start_time = time.time()
        self.last_update = time.time()
        self._display()
    
    def update(
        self,
        increment: int = 1,
        description: Optional[str] = None,
        message: Optional[str] = None
    ):
        """
        Update progress.
        
        Args:
            increment: Amount to increment progress
            description: New description (optional)
            message: Additional message (optional)
        """
        self.current = min(self.current + increment, self.total)
        if description is not None:
            self.description = description
        self.last_update = time.time()
        self._display(message)
    
    def set_progress(self, value: int, message: Optional[str] = None):
        """
        Set absolute progress value.
        
        Args:
            value: New progress value
            message: Additional message (optional)
        """
        self.current = min(max(value, 0), self.total)
        self.last_update = time.time()
        self._display(message)
    
    def finish(self, message: Optional[str] = None):
        """
        Mark progress as complete.
        
        Args:
            message: Completion message (optional)
        """
        self.current = self.total
        self._display(message or "Complete")
        print()  # New line after completion
    
    def _display(self, message: Optional[str] = None):
        """Display the progress indicator."""
        if not self.start_time:
            return
        
        percentage = (self.current / self.total) * 100
        elapsed = time.time() - self.start_time
        
        parts = []
        
        # Add description
        if self.description:
            parts.append(f"{self.description}: ")
        
        # Add progress based on style
        if self.style == ProgressStyle.BAR:
            bar = self._create_bar(percentage)
            parts.append(bar)
        
        elif self.style == ProgressStyle.DOTS:
            dots = " " * (min(self.current // 5, 20))
            parts.append(f"[{dots}]")
        
        elif self.style == ProgressStyle.SPINNER:
            spinner = self.SPINNERS[self.spinner_style][self.spinner_index % 4]
            parts.append(f"{spinner}")
            self.spinner_index += 1
        
        # Add percentage
        if self.style in [ProgressStyle.PERCENTAGE, ProgressStyle.BAR]:
            parts.append(f"{percentage:.1f}%")
        
        elif self.style == ProgressStyle.COUNTER:
            parts.append(f"{self.current}/{self.total}")
        
        # Add time info
        if self.show_time and elapsed > 0:
            time_str = self._format_time(elapsed)
            parts.append(f"[{time_str}]")
        
        # Add ETA
        if self.show_eta and self.current > 0:
            eta = self._calculate_eta(elapsed)
            if eta:
                eta_str = self._format_time(eta)
                parts.append(f"ETA: {eta_str}")
        
        # Add message
        if message:
            parts.append(f"- {message}")
        
        # Build output
        output = "\r" + " ".join(parts)
        
        # Truncate if too long
        max_length = self.width + 50
        if len(output) > max_length:
            output = output[:max_length] + "..."
        
        print(output, end="", flush=True)
    
    def _create_bar(self, percentage: float) -> str:
        """Create a progress bar string."""
        filled = int((percentage / 100) * self.width)
        bar = "█" * filled + "░" * (self.width - filled)
        return f"[{bar}]"
    
    def _calculate_eta(self, elapsed: float) -> Optional[float]:
        """Calculate estimated time remaining."""
        if self.current == 0:
            return None
        
        rate = self.current / elapsed
        if rate == 0:
            return None
        
        remaining = self.total - self.current
        return remaining / rate
    
    def _format_time(self, seconds: float) -> str:
        """Format time in human-readable format."""
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def add_step(self, name: str, total: int = 100) -> 'ProgressStep':
        """
        Add a step to the progress indicator.
        
        Args:
            name: Name of the step
            total: Total items for this step
            
        Returns:
            Created ProgressStep object
        """
        step = ProgressStep(name=name, total=total)
        self.steps.append(step)
        return step
    
    def start_step(self, step_index: int):
        """
        Start a specific step.
        
        Args:
            step_index: Index of the step to start
        """
        if 0 <= step_index < len(self.steps):
            self.current_step_index = step_index
            step = self.steps[step_index]
            step.status = ProgressStatus.IN_PROGRESS
            step.start_time = time.time()
            self.description = f"Step {step_index + 1}/{len(self.steps)}: {step.name}"
    
    def update_step(self, step_index: int, increment: int = 1):
        """
        Update progress for a specific step.
        
        Args:
            step_index: Index of the step to update
            increment: Amount to increment
        """
        if 0 <= step_index < len(self.steps):
            step = self.steps[step_index]
            step.completed = min(step.completed + increment, step.total)
            self.current = sum(s.completed for s in self.steps)
            self.total = sum(s.total for s in self.steps)
    
    def complete_step(self, step_index: int):
        """
        Mark a step as complete.
        
        Args:
            step_index: Index of the step to complete
        """
        if 0 <= step_index < len(self.steps):
            step = self.steps[step_index]
            step.status = ProgressStatus.COMPLETED
            step.end_time = time.time()
            step.completed = step.total
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the progress.
        
        Returns:
            Dictionary with progress summary
        """
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        return {
            "total": self.total,
            "current": self.current,
            "percentage": (self.current / self.total) * 100 if self.total > 0 else 0,
            "elapsed_time": elapsed,
            "start_time": self.start_time,
            "steps": [
                {
                    "name": step.name,
                    "status": step.status.value,
                    "percentage": step.percentage,
                    "elapsed_time": step.elapsed_time
                }
                for step in self.steps
            ]
        }


class MultiProgressIndicator:
    """Manages multiple progress indicators concurrently."""
    
    def __init__(self, max_lines: int = 5):
        """
        Initialize multi-progress indicator.
        
        Args:
            max_lines: Maximum number of progress lines to display
        """
        self.indicators: Dict[str, ProgressIndicator] = {}
        self.max_lines = max_lines
        self.last_display: Optional[str] = None
    
    def add_indicator(
        self,
        key: str,
        total: int = 100,
        description: str = "",
        style: ProgressStyle = ProgressStyle.BAR
    ) -> ProgressIndicator:
        """
        Add a new progress indicator.
        
        Args:
            key: Unique key for the indicator
            total: Total items
            description: Description
            style: Progress style
            
        Returns:
            Created ProgressIndicator
        """
        indicator = ProgressIndicator(total, description, style)
        self.indicators[key] = indicator
        return indicator
    
    def update(self, key: str, increment: int = 1, message: Optional[str] = None):
        """Update a specific indicator."""
        if key in self.indicators:
            self.indicators[key].update(increment, message=message)
            self._display()
    
    def _display(self):
        """Display all indicators."""
        lines = []
        
        for key, indicator in self.indicators.items():
            percentage = (indicator.current / indicator.total) * 100
            elapsed = time.time() - indicator.start_time if indicator.start_time else 0
            
            line = f"{key}: {percentage:.1f}%"
            if elapsed > 0:
                line += f" ({indicator._format_time(elapsed)})"
            
            lines.append(line)
        
        # Limit to max_lines
        if len(lines) > self.max_lines:
            lines = lines[:self.max_lines]
            lines.append(f"... and {len(self.indicators) - self.max_lines} more")
        
        output = "\n".join(lines)
        
        # Clear previous display
        if self.last_display:
            lines_to_clear = len(self.last_display.split("\n"))
            sys.stdout.write("\033[F" * lines_to_clear)
        
        print(output)
        self.last_display = output


def create_progress(
    total: int = 100,
    description: str = "",
    style: ProgressStyle = ProgressStyle.BAR
) -> ProgressIndicator:
    """Create a progress indicator."""
    return ProgressIndicator(total, description, style)


def with_progress(
    total: int = 100,
    description: str = "",
    style: ProgressStyle = ProgressStyle.BAR
) -> Callable:
    """
    Decorator to wrap a function with progress tracking.
    
    Args:
        total: Total items
        description: Description
        style: Progress style
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            progress = ProgressIndicator(total, description, style)
            progress.start()
            
            try:
                # Call function with progress as additional argument
                result = func(*args, **kwargs, progress=progress)
                progress.finish("Complete")
                return result
            except Exception as e:
                progress.finish(f"Failed: {str(e)}")
                raise
        
        return wrapper
    return decorator