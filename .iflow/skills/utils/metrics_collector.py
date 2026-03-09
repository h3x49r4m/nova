"""Metrics Collector - Collects and tracks operational metrics.

This module provides metrics collection for execution times, success rates,
and other operational metrics for monitoring and analysis.
"""

import json
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .exceptions import IFlowError, ErrorCode


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class MetricCategory(Enum):
    """Categories of metrics."""
    EXECUTION = "execution"
    SUCCESS = "success"
    ERROR = "error"
    PERFORMANCE = "performance"
    RESOURCE = "resource"
    CUSTOM = "custom"


@dataclass
class Metric:
    """Represents a single metric."""
    name: str
    metric_type: MetricType
    category: MetricCategory
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "category": self.category.value,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
            "metadata": self.metadata
        }


@dataclass
class HistogramBucket:
    """Histogram bucket for value distribution."""
    upper_bound: float
    count: int = 0


@dataclass
class Histogram:
    """Histogram metric for value distribution."""
    name: str
    buckets: List[HistogramBucket] = field(default_factory=list)
    sum: float = 0.0
    count: int = 0
    
    def observe(self, value: float):
        """Observe a value."""
        self.count += 1
        self.sum += value
        
        for bucket in self.buckets:
            if value <= bucket.upper_bound:
                bucket.count += 1
    
    def get_percentile(self, percentile: float) -> float:
        """Get approximate percentile value."""
        if self.count == 0:
            return 0.0
        
        target_count = int(self.count * percentile / 100)
        cumulative = 0
        
        for bucket in self.buckets:
            cumulative += bucket.count
            if cumulative >= target_count:
                return bucket.upper_bound
        
        return self.buckets[-1].upper_bound


@dataclass
class Timer:
    """Timer metric for duration tracking."""
    name: str
    min: float = float('inf')
    max: float = 0.0
    sum: float = 0.0
    count: int = 0
    values: List[float] = field(default_factory=list)
    max_values: int = 1000
    
    def record(self, duration: float):
        """Record a duration."""
        self.count += 1
        self.sum += duration
        self.min = min(self.min, duration)
        self.max = max(self.max, duration)
        
        # Keep only last N values
        self.values.append(duration)
        if len(self.values) > self.max_values:
            self.values.pop(0)
    
    def get_average(self) -> float:
        """Get average duration."""
        return self.sum / self.count if self.count > 0 else 0.0
    
    def get_percentile(self, percentile: float) -> float:
        """Get percentile duration."""
        if not self.values:
            return 0.0
        
        sorted_values = sorted(self.values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


class MetricsCollector:
    """Collects and manages operational metrics."""
    
    def __init__(
        self,
        metrics_file: Optional[Path] = None,
        enable_persistence: bool = True
    ):
        """
        Initialize metrics collector.
        
        Args:
            metrics_file: File to persist metrics
            enable_persistence: Whether to persist metrics to file
        """
        self.metrics_file = metrics_file or (Path.cwd() / ".iflow" / "metrics" / "metrics.json")
        self.enable_persistence = enable_persistence
        
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, Histogram] = {}
        self.timers: Dict[str, Timer] = {}
        self.custom_metrics: List[Metric] = []
        
        self._lock = threading.RLock()
        
        if enable_persistence:
            self._load_metrics()
    
    def _load_metrics(self):
        """Load metrics from file."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                
                self.counters.update(data.get("counters", {}))
                self.gauges.update(data.get("gauges", {}))
                
                # Load histograms
                for name, hist_data in data.get("histograms", {}).items():
                    hist = Histogram(name)
                    hist.sum = hist_data.get("sum", 0.0)
                    hist.count = hist_data.get("count", 0)
                    for bucket_data in hist_data.get("buckets", []):
                        bucket = HistogramBucket(bucket_data["upper_bound"])
                        bucket.count = bucket_data["count"]
                        hist.buckets.append(bucket)
                    self.histograms[name] = hist
                
                # Load timers
                for name, timer_data in data.get("timers", {}).items():
                    timer = Timer(name)
                    timer.min = timer_data.get("min", float('inf'))
                    timer.max = timer_data.get("max", 0.0)
                    timer.sum = timer_data.get("sum", 0.0)
                    timer.count = timer_data.get("count", 0)
                    timer.values = timer_data.get("values", [])
                    self.timers[name] = timer
                
            except (json.JSONDecodeError, IOError):
                pass
    
    def _save_metrics(self):
        """Save metrics to file."""
        if not self.enable_persistence:
            return
        
        try:
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {
                    name: {
                        "sum": hist.sum,
                        "count": hist.count,
                        "buckets": [
                            {"upper_bound": b.upper_bound, "count": b.count}
                            for b in hist.buckets
                        ]
                    }
                    for name, hist in self.histograms.items()
                },
                "timers": {
                    name: {
                        "min": timer.min if timer.min != float('inf') else 0,
                        "max": timer.max,
                        "sum": timer.sum,
                        "count": timer.count,
                        "values": timer.values
                    }
                    for name, timer in self.timers.items()
                },
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
        
        except IOError as e:
            raise IFlowError(
                f"Failed to save metrics: {str(e)}",
                ErrorCode.FILE_WRITE_ERROR
            )
    
    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Increment a counter metric.
        
        Args:
            name: Counter name
            value: Value to increment by
            labels: Optional labels
        """
        with self._lock:
            if labels:
                full_name = f"{name}.{self._labels_to_string(labels)}"
            else:
                full_name = name
            
            self.counters[full_name] += value
    
    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Set a gauge metric.
        
        Args:
            name: Gauge name
            value: Gauge value
            labels: Optional labels
        """
        with self._lock:
            if labels:
                full_name = f"{name}.{self._labels_to_string(labels)}"
            else:
                full_name = name
            
            self.gauges[full_name] = value
    
    def record_histogram(
        self,
        name: str,
        value: float,
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Record a value in a histogram.
        
        Args:
            name: Histogram name
            value: Value to record
            buckets: Bucket boundaries
            labels: Optional labels
        """
        with self._lock:
            if labels:
                full_name = f"{name}.{self._labels_to_string(labels)}"
            else:
                full_name = name
            
            if full_name not in self.histograms:
                if buckets is None:
                    buckets = [0.1, 1.0, 5.0, 10.0, 50.0, 100.0, 500.0, 1000.0]
                
                self.histograms[full_name] = Histogram(
                    full_name,
                    [HistogramBucket(b) for b in buckets]
                )
            
            self.histograms[full_name].observe(value)
    
    def record_timer(
        self,
        name: str,
        duration: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Record a duration in a timer.
        
        Args:
            name: Timer name
            duration: Duration in seconds
            labels: Optional labels
        """
        with self._lock:
            if labels:
                full_name = f"{name}.{self._labels_to_string(labels)}"
            else:
                full_name = name
            
            if full_name not in self.timers:
                self.timers[full_name] = Timer(full_name)
            
            self.timers[full_name].record(duration)
    
    def record_custom_metric(
        self,
        name: str,
        value: float,
        category: MetricCategory = MetricCategory.CUSTOM,
        labels: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a custom metric.
        
        Args:
            name: Metric name
            value: Metric value
            category: Metric category
            labels: Optional labels
            metadata: Optional metadata
        """
        with self._lock:
            metric = Metric(
                name=name,
                metric_type=MetricType.GAUGE,
                category=category,
                value=value,
                labels=labels or {},
                metadata=metadata or {}
            )
            self.custom_metrics.append(metric)
    
    def get_counter(self, name: str) -> float:
        """
        Get counter value.
        
        Args:
            name: Counter name
            
        Returns:
            Counter value
        """
        return self.counters.get(name, 0.0)
    
    def get_gauge(self, name: str) -> float:
        """
        Get gauge value.
        
        Args:
            name: Gauge name
            
        Returns:
            Gauge value
        """
        return self.gauges.get(name, 0.0)
    
    def get_histogram(self, name: str) -> Optional[Histogram]:
        """
        Get histogram.
        
        Args:
            name: Histogram name
            
        Returns:
            Histogram or None
        """
        return self.histograms.get(name)
    
    def get_timer(self, name: str) -> Optional[Timer]:
        """
        Get timer.
        
        Args:
            name: Timer name
            
        Returns:
            Timer or None
        """
        return self.timers.get(name)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics.
        
        Returns:
            Dictionary of all metrics
        """
        with self._lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {
                    name: {
                        "sum": hist.sum,
                        "count": hist.count,
                        "buckets": [
                            {"upper_bound": b.upper_bound, "count": b.count}
                            for b in hist.buckets
                        ]
                    }
                    for name, hist in self.histograms.items()
                },
                "timers": {
                    name: {
                        "min": timer.min if timer.min != float('inf') else 0,
                        "max": timer.max,
                        "sum": timer.sum,
                        "count": timer.count,
                        "average": timer.get_average(),
                        "p50": timer.get_percentile(50),
                        "p95": timer.get_percentile(95),
                        "p99": timer.get_percentile(99)
                    }
                    for name, timer in self.timers.items()
                },
                "custom": [m.to_dict() for m in self.custom_metrics]
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get metrics summary.
        
        Returns:
            Summary statistics
        """
        with self._lock:
            return {
                "total_metrics": (
                    len(self.counters) +
                    len(self.gauges) +
                    len(self.histograms) +
                    len(self.timers) +
                    len(self.custom_metrics)
                ),
                "counters": len(self.counters),
                "gauges": len(self.gauges),
                "histograms": len(self.histograms),
                "timers": len(self.timers),
                "custom": len(self.custom_metrics),
                "total_recordings": (
                    sum(self.counters.values()) +
                    sum(self.timers[t].count for t in self.timers) +
                    sum(self.histograms[h].count for h in self.histograms)
                )
            }
    
    def reset_metrics(self):
        """Reset all metrics."""
        with self._lock:
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.timers.clear()
            self.custom_metrics.clear()
    
    def export_metrics(self, format: str = "json") -> str:
        """
        Export metrics.
        
        Args:
            format: Export format (json, prometheus)
            
        Returns:
            Exported metrics string
        """
        metrics = self.get_all_metrics()
        
        if format == "json":
            return json.dumps(metrics, indent=2)
        
        elif format == "prometheus":
            lines = []
            
            # Counters
            for name, value in self.counters.items():
                lines.append(f"iflow_counter_{name} {value}")
            
            # Gauges
            for name, value in self.gauges.items():
                lines.append(f"iflow_gauge_{name} {value}")
            
            # Timers
            for name, timer in self.timers.items():
                lines.append(f"iflow_timer_{name}_sum {timer.sum}")
                lines.append(f"iflow_timer_{name}_count {timer.count}")
                lines.append(f"iflow_timer_{name}_avg {timer.get_average()}")
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def save(self):
        """Save metrics to file."""
        self._save_metrics()
    
    def _labels_to_string(self, labels: Dict[str, str]) -> str:
        """
        Convert labels to string.
        
        Args:
            labels: Labels dictionary
            
        Returns:
            String representation
        """
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))


class MetricsTimer:
    """Context manager for timing operations."""
    
    def __init__(
        self,
        collector: MetricsCollector,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        Initialize timer context manager.
        
        Args:
            collector: Metrics collector
            name: Timer name
            labels: Optional labels
        """
        self.collector = collector
        self.name = name
        self.labels = labels
        self.start_time = None
    
    def __enter__(self) -> 'MetricsTimer':
        """Enter context."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.collector.record_timer(self.name, duration, self.labels)


# Global metrics collector
_global_collector: Optional[MetricsCollector] = None


def get_metrics_collector(
    metrics_file: Optional[Path] = None,
    enable_persistence: bool = True
) -> MetricsCollector:
    """
    Get or create global metrics collector.
    
    Args:
        metrics_file: File to persist metrics
        enable_persistence: Whether to persist metrics
        
    Returns:
        MetricsCollector instance
    """
    global _global_collector
    
    if _global_collector is None:
        _global_collector = MetricsCollector(metrics_file, enable_persistence)
    
    return _global_collector


def measure_time(
    name: str,
    labels: Optional[Dict[str, str]] = None,
    collector: Optional[MetricsCollector] = None
):
    """
    Decorator for measuring function execution time.
    
    Args:
        name: Timer name
        labels: Optional labels
        collector: Optional metrics collector
        
    Returns:
        Decorator function
    """
    if collector is None:
        collector = get_metrics_collector()
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with MetricsTimer(collector, name, labels):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def count_calls(
    name: str,
    labels: Optional[Dict[str, str]] = None,
    collector: Optional[MetricsCollector] = None
):
    """
    Decorator for counting function calls.
    
    Args:
        name: Counter name
        labels: Optional labels
        collector: Optional metrics collector
        
    Returns:
        Decorator function
    """
    if collector is None:
        collector = get_metrics_collector()
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            collector.increment_counter(name, labels=labels)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def track_success_rate(
    name: str,
    labels: Optional[Dict[str, str]] = None,
    collector: Optional[MetricsCollector] = None
):
    """
    Decorator for tracking function success rate.
    
    Args:
        name: Metric name prefix
        labels: Optional labels
        collector: Optional metrics collector
        
    Returns:
        Decorator function
    """
    if collector is None:
        collector = get_metrics_collector()
    
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                collector.increment_counter(f"{name}_success", labels=labels)
                return result
            except Exception as e:
                collector.increment_counter(f"{name}_error", labels=labels)
                raise
        return wrapper
    return decorator
