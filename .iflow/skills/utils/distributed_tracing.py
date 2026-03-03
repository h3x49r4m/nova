"""Distributed Tracing - Tracks execution across distributed workflows.

This module provides distributed tracing capabilities for tracking execution
flow across multiple skills, pipelines, and operations.
"""

import json
import time
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .exceptions import IFlowError, ErrorCode


class SpanStatus(Enum):
    """Status of a span."""
    STARTED = "started"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"
    CANCELLED = "cancelled"


class SpanKind(Enum):
    """Kind of span."""
    INTERNAL = "internal"
    CLIENT = "client"
    SERVER = "server"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class SpanEvent:
    """Event within a span."""
    name: str
    timestamp: float = field(default_factory=time.time)
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "attributes": self.attributes
        }


@dataclass
class SpanLink:
    """Link to another span."""
    trace_id: str
    span_id: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "attributes": self.attributes
        }


@dataclass
class Span:
    """Represents a span in a trace."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    name: str = ""
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.STARTED
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "attributes": self.attributes,
            "events": [e.to_dict() for e in self.events],
            "links": [l.to_dict() for l in self.links]
        }
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add event to span."""
        event = SpanEvent(name, attributes=attributes or {})
        self.events.append(event)
    
    def add_attribute(self, key: str, value: Any):
        """Add attribute to span."""
        self.attributes[key] = value
    
    def add_link(self, link: SpanLink):
        """Add link to span."""
        self.links.append(link)
    
    def finish(self, status: SpanStatus = SpanStatus.FINISHED):
        """Finish the span."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = status
    
    def record_error(self, error: Exception):
        """Record error in span."""
        self.status = SpanStatus.ERROR
        self.add_event("error", {
            "type": type(error).__name__,
            "message": str(error)
        })
        self.add_attribute("error", True)
        self.add_attribute("error.type", type(error).__name__)
        self.add_attribute("error.message", str(error))


@dataclass
class Trace:
    """Represents a distributed trace."""
    trace_id: str
    root_span_id: str
    spans: Dict[str, Span] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "root_span_id": self.root_span_id,
            "spans": {span_id: span.to_dict() for span_id, span in self.spans.items()},
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "attributes": self.attributes
        }
    
    def add_span(self, span: Span):
        """Add span to trace."""
        self.spans[span.span_id] = span
    
    def get_span(self, span_id: str) -> Optional[Span]:
        """Get span by ID."""
        return self.spans.get(span_id)
    
    def get_root_span(self) -> Optional[Span]:
        """Get root span."""
        return self.spans.get(self.root_span_id)
    
    def finish(self):
        """Finish the trace."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        
        # Finish all running spans
        for span in self.spans.values():
            if span.status == SpanStatus.RUNNING or span.status == SpanStatus.STARTED:
                span.finish(SpanStatus.CANCELLED)


class Tracer:
    """Creates and manages traces and spans."""
    
    def __init__(
        self,
        service_name: str,
        trace_file: Optional[Path] = None,
        enable_persistence: bool = True
    ):
        """
        Initialize tracer.
        
        Args:
            service_name: Name of the service
            trace_file: File to persist traces
            enable_persistence: Whether to persist traces
        """
        self.service_name = service_name
        self.trace_file = trace_file or (Path.cwd() / ".iflow" / "traces" / "traces.jsonl")
        self.enable_persistence = enable_persistence
        
        self.traces: Dict[str, Trace] = {}
        self._current_span: Optional[Span] = None
        self._lock = threading.RLock()
        
        if enable_persistence:
            self._trace_file.parent.mkdir(parents=True, exist_ok=True)
    
    def start_trace(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """
        Start a new trace.
        
        Args:
            name: Name of the root span
            kind: Kind of span
            attributes: Optional attributes
            
        Returns:
            Root span
        """
        with self._lock:
            trace_id = str(uuid.uuid4())
            span_id = str(uuid.uuid4())
            
            span = Span(
                trace_id=trace_id,
                span_id=span_id,
                name=name,
                kind=kind,
                attributes=attributes or {}
            )
            
            trace = Trace(
                trace_id=trace_id,
                root_span_id=span_id
            )
            
            trace.add_span(span)
            self.traces[trace_id] = trace
            self._current_span = span
            
            return span
    
    def start_span(
        self,
        name: str,
        parent_span: Optional[Span] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """
        Start a new span.
        
        Args:
            name: Name of the span
            parent_span: Parent span (uses current if None)
            kind: Kind of span
            attributes: Optional attributes
            
        Returns:
            New span
        """
        with self._lock:
            if parent_span is None:
                parent_span = self._current_span
            
            if parent_span is None:
                # Start a new trace
                return self.start_trace(name, kind, attributes)
            
            trace_id = parent_span.trace_id
            span_id = str(uuid.uuid4())
            
            span = Span(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span.span_id,
                name=name,
                kind=kind,
                attributes=attributes or {}
            )
            
            trace = self.traces.get(trace_id)
            if trace:
                trace.add_span(span)
                self._current_span = span
            
            return span
    
    def get_current_span(self) -> Optional[Span]:
        """Get current active span."""
        return self._current_span
    
    def finish_span(self, span: Span, status: SpanStatus = SpanStatus.FINISHED):
        """
        Finish a span.
        
        Args:
            span: Span to finish
            status: Final status
        """
        with self._lock:
            span.finish(status)
            
            # If this is the root span, finish the trace
            trace = self.traces.get(span.trace_id)
            if trace and span.span_id == trace.root_span_id:
                trace.finish()
                if self.enable_persistence:
                    self._persist_trace(trace)
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """
        Get trace by ID.
        
        Args:
            trace_id: Trace ID
            
        Returns:
            Trace or None
        """
        return self.traces.get(trace_id)
    
    def get_all_traces(self) -> List[Trace]:
        """Get all traces."""
        return list(self.traces.values())
    
    def _persist_trace(self, trace: Trace):
        """Persist trace to file."""
        try:
            with open(self.trace_file, 'a') as f:
                f.write(json.dumps(trace.to_dict()) + '\n')
        except IOError as e:
            raise IFlowError(
                f"Failed to persist trace: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def export_trace(self, trace_id: str, format: str = "json") -> str:
        """
        Export trace.
        
        Args:
            trace_id: Trace ID
            format: Export format (json, jaeger)
            
        Returns:
            Exported trace string
        """
        trace = self.get_trace(trace_id)
        if not trace:
            return ""
        
        if format == "json":
            return json.dumps(trace.to_dict(), indent=2)
        
        elif format == "jaeger":
            # Jaeger format (simplified)
            jaeger_trace = {
                "traceID": trace.trace_id,
                "spans": []
            }
            
            for span in trace.spans.values():
                jaeger_span = {
                    "traceID": span.trace_id,
                    "spanID": span.span_id,
                    "operationName": span.name,
                    "startTime": int(span.start_time * 1_000_000),  # microseconds
                    "duration": int(span.duration * 1_000_000) if span.duration else 0,
                    "tags": [
                        {"key": k, "value": str(v)}
                        for k, v in span.attributes.items()
                    ],
                    "logs": [
                        {
                            "timestamp": int(event.timestamp * 1_000_000),
                            "fields": [
                                {"key": "event", "value": event.name}
                            ] + [
                                {"key": k, "value": str(v)}
                                for k, v in event.attributes.items()
                            ]
                        }
                        for event in span.events
                    ]
                }
                
                if span.parent_span_id:
                    jaeger_span["references"] = [{
                        "refType": "CHILD_OF",
                        "traceID": span.trace_id,
                        "spanID": span.parent_span_id
                    }]
                
                jaeger_trace["spans"].append(jaeger_span)
            
            return json.dumps([jaeger_trace], indent=2)
        
        else:
            raise ValueError(f"Unknown format: {format}")


class SpanContext:
    """Context manager for creating spans."""
    
    def __init__(
        self,
        tracer: Tracer,
        name: str,
        parent_span: Optional[Span] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize span context manager.
        
        Args:
            tracer: Tracer instance
            name: Span name
            parent_span: Parent span
            kind: Span kind
            attributes: Optional attributes
        """
        self.tracer = tracer
        self.name = name
        self.parent_span = parent_span
        self.kind = kind
        self.attributes = attributes
        self.span: Optional[Span] = None
    
    def __enter__(self) -> Span:
        """Enter context."""
        self.span = self.tracer.start_span(
            self.name,
            self.parent_span,
            self.kind,
            self.attributes
        )
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if self.span:
            if exc_type is not None:
                self.span.record_error(exc_val)
            self.tracer.finish_span(self.span)


# Global tracer
_global_tracer: Optional[Tracer] = None


def get_tracer(
    service_name: str = "iflow",
    trace_file: Optional[Path] = None,
    enable_persistence: bool = True
) -> Tracer:
    """
    Get or create global tracer.
    
    Args:
        service_name: Service name
        trace_file: File to persist traces
        enable_persistence: Whether to persist traces
        
    Returns:
        Tracer instance
    """
    global _global_tracer
    
    if _global_tracer is None:
        _global_tracer = Tracer(service_name, trace_file, enable_persistence)
    
    return _global_tracer


def trace(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    tracer: Optional[Tracer] = None
):
    """
    Decorator for tracing function execution.
    
    Args:
        name: Span name
        kind: Span kind
        attributes: Optional attributes
        tracer: Optional tracer
        
    Returns:
        Decorator function
    """
    if tracer is None:
        tracer = get_tracer()
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with SpanContext(tracer, name, kind=kind, attributes=attributes):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def trace_async(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    tracer: Optional[Tracer] = None
):
    """
    Decorator for tracing async function execution.
    
    Args:
        name: Span name
        kind: Span kind
        attributes: Optional attributes
        tracer: Optional tracer
        
    Returns:
        Decorator function
    """
    if tracer is None:
        tracer = get_tracer()
    
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            with SpanContext(tracer, name, kind=kind, attributes=attributes):
                return await func(*args, **kwargs)
        return wrapper
    return decorator
