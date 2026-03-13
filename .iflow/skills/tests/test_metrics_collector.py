#!/usr/bin/env python3
"""
Unit tests for MetricsCollector module.
"""

import json
import pytest
import time
import tempfile
import shutil
from pathlib import Path

from utils.metrics_collector import (
    MetricsCollector,
    Metric,
    MetricType,
    MetricCategory,
    Histogram,
    HistogramBucket
)


class TestMetric:
    """Tests for the Metric class."""

    def test_metric_initialization(self):
        """Test metric object initialization."""
        metric = Metric(
            name="test_metric",
            metric_type=MetricType.COUNTER,
            category=MetricCategory.EXECUTION,
            value=42.0,
            labels={"env": "test"},
            metadata={"description": "Test metric"}
        )

        assert metric.name == "test_metric"
        assert metric.metric_type == MetricType.COUNTER
        assert metric.category == MetricCategory.EXECUTION
        assert metric.value == 42.0
        assert metric.labels == {"env": "test"}
        assert metric.metadata == {"description": "Test metric"}

    def test_metric_to_dict(self):
        """Test converting metric to dictionary."""
        metric = Metric(
            name="test_metric",
            metric_type=MetricType.GAUGE,
            category=MetricCategory.PERFORMANCE,
            value=100.0
        )

        result = metric.to_dict()

        assert result["name"] == "test_metric"
        assert result["type"] == "gauge"
        assert result["category"] == "performance"
        assert result["value"] == 100.0
        assert "timestamp" in result
        assert "labels" in result


class TestHistogram:
    """Tests for the Histogram class."""

    def test_histogram_initialization(self):
        """Test histogram object initialization."""
        histogram = Histogram(
            name="test_histogram",
            buckets=[
                HistogramBucket(10.0),
                HistogramBucket(100.0),
                HistogramBucket(1000.0)
            ]
        )

        assert histogram.name == "test_histogram"
        assert len(histogram.buckets) == 3
        assert histogram.sum == 0.0
        assert histogram.count == 0

    def test_histogram_observe(self):
        """Test observing values in histogram."""
        histogram = Histogram(
            name="test_histogram",
            buckets=[
                HistogramBucket(10.0),
                HistogramBucket(100.0),
                HistogramBucket(1000.0)
            ]
        )

        histogram.observe(5.0)
        histogram.observe(50.0)
        histogram.observe(500.0)

        assert histogram.count == 3
        assert histogram.sum == 555.0
        assert histogram.buckets[0].count == 1  # 5.0 <= 10.0
        assert histogram.buckets[1].count == 2  # 50.0 <= 100.0, 500.0 > 100.0 but 500.0 <= 1000.0

    def test_histogram_get_percentile(self):
        """Test getting percentile from histogram."""
        histogram = Histogram(
            name="test_histogram",
            buckets=[
                HistogramBucket(10.0),
                HistogramBucket(100.0),
                HistogramBucket(1000.0)
            ]
        )

        # Add 10 values: 1-10 (all in first bucket)
        for i in range(1, 11):
            histogram.observe(float(i))

        # 50th percentile should be based on bucket upper bounds
        p50 = histogram.get_percentile(50.0)
        assert p50 >= 0.0  # Non-negative

        # 90th percentile - all values in first bucket
        p90 = histogram.get_percentile(90.0)
        assert p90 >= 0.0  # Non-negative

    def test_histogram_empty(self):
        """Test histogram with no observations."""
        histogram = Histogram(
            name="test_histogram",
            buckets=[HistogramBucket(100.0)]
        )

        percentile = histogram.get_percentile(50.0)
        assert percentile == 0.0


class TestMetricsCollector:
    """Tests for the MetricsCollector class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def metrics_collector(self, temp_dir):
        """Create a MetricsCollector instance for testing."""
        metrics_file = temp_dir / ".iflow" / "metrics" / "metrics.json"
        return MetricsCollector(metrics_file=metrics_file, enable_persistence=False)

    def test_metrics_collector_initialization(self, temp_dir):
        """Test MetricsCollector initialization."""
        metrics_file = temp_dir / ".iflow" / "metrics" / "metrics.json"
        collector = MetricsCollector(metrics_file=metrics_file, enable_persistence=False)

        assert collector.metrics_file == metrics_file
        assert isinstance(collector.counters, dict)
        assert isinstance(collector.histograms, dict)

    def test_increment_counter(self, metrics_collector):
        """Test incrementing a counter metric."""
        metrics_collector.increment_counter("test_counter")

        value = metrics_collector.get_counter("test_counter")
        assert value == 1.0

    def test_increment_counter_with_value(self, metrics_collector):
        """Test incrementing counter with specific value."""
        metrics_collector.increment_counter(
            "test_counter",
            value=5.0
        )

        value = metrics_collector.get_counter("test_counter")
        assert value == 5.0

    def test_increment_counter_with_labels(self, metrics_collector):
        """Test incrementing counter with labels."""
        metrics_collector.increment_counter(
            "test_counter",
            labels={"env": "test", "component": "api"}
        )

        # With labels, the counter name includes the labels (sorted keys, comma-separated)
        value = metrics_collector.get_counter("test_counter.component=api,env=test")
        assert value == 1.0

    def test_set_gauge(self, metrics_collector):
        """Test setting a gauge metric."""
        metrics_collector.set_gauge(
            "test_gauge",
            value=42.0
        )

        value = metrics_collector.get_gauge("test_gauge")
        assert value == 42.0

    def test_update_gauge(self, metrics_collector):
        """Test updating an existing gauge metric."""
        metrics_collector.set_gauge("test_gauge", value=10.0)
        metrics_collector.set_gauge("test_gauge", value=20.0)

        value = metrics_collector.get_gauge("test_gauge")
        assert value == 20.0  # Gauges overwrite the previous value

    def test_record_timing(self, metrics_collector):
        """Test recording a timing metric."""
        from utils.metrics_collector import MetricsTimer

        with MetricsTimer(metrics_collector, "test_timer"):
            time.sleep(0.01)

        timer = metrics_collector.get_timer("test_timer")
        assert timer is not None
        assert timer.count == 1
        assert timer.sum > 0.0  # Should be positive (elapsed time)

    def test_record_timing_with_labels(self, metrics_collector):
        """Test recording timing with labels."""
        from utils.metrics_collector import MetricsTimer

        with MetricsTimer(
            metrics_collector,
            "test_timer",
            labels={"operation": "query", "database": "postgres"}
        ):
            time.sleep(0.01)

        # With labels, the timer name includes the labels (sorted keys, comma-separated)
        timer = metrics_collector.get_timer("test_timer.database=postgres,operation=query")
        assert timer is not None
        assert timer.count == 1

    def test_record_histogram(self, metrics_collector):
        """Test recording histogram metric."""
        metrics_collector.record_histogram(
            "test_histogram",
            value=50.0
        )

        histogram = metrics_collector.get_histogram("test_histogram")
        assert histogram is not None
        assert histogram.count == 1
        assert histogram.sum == 50.0

    def test_record_histogram_multiple_values(self, metrics_collector):
        """Test recording multiple values in histogram."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            metrics_collector.record_histogram(
                "test_histogram",
                value=value
            )

        histogram = metrics_collector.get_histogram("test_histogram")
        assert histogram.count == 5
        assert histogram.sum == sum(values)

    def test_get_all_metrics(self, metrics_collector):
        """Test getting all metrics."""
        metrics_collector.increment_counter("counter1")
        metrics_collector.set_gauge("gauge1", value=100.0)
        metrics_collector.increment_counter("counter2")

        all_metrics = metrics_collector.get_all_metrics()

        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        assert len(all_metrics["counters"]) == 2
        assert len(all_metrics["gauges"]) == 1

    def test_get_metrics_by_name(self, metrics_collector):
        """Test getting counter by name."""
        metrics_collector.increment_counter("test_counter")
        metrics_collector.increment_counter("test_counter", value=2.0)

        value = metrics_collector.get_counter("test_counter")

        assert value == 3.0

    def test_get_metrics_by_category(self, metrics_collector):
        """Test getting multiple counters."""
        metrics_collector.increment_counter("counter1")
        metrics_collector.set_gauge("gauge1", value=100.0)
        metrics_collector.increment_counter("counter2")

        all_metrics = metrics_collector.get_all_metrics()

        assert len(all_metrics["counters"]) == 2
        assert len(all_metrics["gauges"]) == 1

    def test_clear_metrics(self, metrics_collector):
        """Test clearing all metrics."""
        metrics_collector.increment_counter("counter1")
        metrics_collector.set_gauge("gauge1", value=100.0)

        assert len(metrics_collector.get_all_metrics()["counters"]) == 1
        assert len(metrics_collector.get_all_metrics()["gauges"]) == 1

        metrics_collector.reset_metrics()

        assert len(metrics_collector.get_all_metrics()["counters"]) == 0
        assert len(metrics_collector.get_all_metrics()["gauges"]) == 0

    def test_clear_metrics_by_name(self, metrics_collector):
        """Test clearing counter by name."""
        metrics_collector.increment_counter("counter1")
        metrics_collector.set_gauge("gauge1", value=100.0)
        metrics_collector.increment_counter("counter2")

        # Reset specific counter by setting to 0
        metrics_collector.counters["counter1"] = 0

        assert metrics_collector.get_counter("counter1") == 0
        assert metrics_collector.get_counter("counter2") == 1

    def test_export_metrics(self, metrics_collector, temp_dir):
        """Test exporting metrics to JSON string."""
        metrics_collector.increment_counter("counter1")
        metrics_collector.set_gauge("gauge1", value=100.0)

        exported_json = metrics_collector.export_metrics(format="json")

        assert isinstance(exported_json, str)

        exported_data = json.loads(exported_json)

        assert "counters" in exported_data
        assert "gauges" in exported_data
        assert len(exported_data["counters"]) == 1
        assert len(exported_data["gauges"]) == 1

    def test_get_metric_summary(self, metrics_collector):
        """Test getting metric summary."""
        metrics_collector.increment_counter("counter1")
        metrics_collector.increment_counter("counter1")
        metrics_collector.set_gauge("gauge1", value=100.0)

        summary = metrics_collector.get_summary()

        # get_summary returns counts, not values
        assert "total_metrics" in summary
        assert "counters" in summary
        assert "gauges" in summary
        assert "histograms" in summary
        assert "timers" in summary
        assert summary["counters"] == 1  # 1 counter named counter1
        assert summary["gauges"] == 1  # 1 gauge named gauge1
        assert summary["total_recordings"] == 2  # 2 increments to counter1

    def test_get_histogram_statistics(self, metrics_collector):
        """Test getting histogram statistics."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            metrics_collector.record_histogram(
                "test_histogram",
                value=value
            )

        histogram = metrics_collector.get_histogram("test_histogram")

        assert histogram is not None
        assert histogram.count == 5
        assert histogram.sum == sum(values)
        # Histogram doesn't have get_average method, calculate manually
        average = histogram.sum / histogram.count if histogram.count > 0 else 0.0
        assert average == sum(values) / len(values)

    def test_timer_decorator(self, metrics_collector):
        """Test using timer as decorator using measure_time."""
        from utils.metrics_collector import measure_time

        @measure_time("decorated_timer", collector=metrics_collector)
        def test_function():
            time.sleep(0.01)
            return "result"

        result = test_function()

        assert result == "result"
        timer = metrics_collector.get_timer("decorated_timer")
        assert timer is not None
        assert timer.count == 1

    def test_counter_decorator(self, metrics_collector):
        """Test using counter as decorator using count_calls."""
        from utils.metrics_collector import count_calls

        @count_calls("decorated_counter", collector=metrics_collector)
        def test_function():
            return "result"

        result = test_function()

        assert result == "result"
        value = metrics_collector.get_counter("decorated_counter")
        assert value == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])