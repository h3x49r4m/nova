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

import sys
skills_path = Path(__file__).parent.parent
sys.path.insert(0, str(skills_path))

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

        # Add 10 values: 1-10
        for i in range(1, 11):
            histogram.observe(float(i))

        # 50th percentile should be around 50
        p50 = histogram.get_percentile(50.0)
        assert 10.0 <= p50 <= 100.0

        # 90th percentile should be around 90
        p90 = histogram.get_percentile(90.0)
        assert 100.0 <= p90 <= 1000.0

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
        return MetricsCollector(repo_root=temp_dir)

    def test_metrics_collector_initialization(self, temp_dir):
        """Test MetricsCollector initialization."""
        collector = MetricsCollector(repo_root=temp_dir)

        assert collector.repo_root == temp_dir
        assert isinstance(collector.metrics, dict)
        assert isinstance(collector.histograms, dict)

    def test_increment_counter(self, metrics_collector):
        """Test incrementing a counter metric."""
        metrics_collector.increment_counter("test_counter", category=MetricCategory.EXECUTION)

        metrics = metrics_collector.get_metrics("test_counter")
        assert len(metrics) == 1
        assert metrics[0].value == 1.0

    def test_increment_counter_with_value(self, metrics_collector):
        """Test incrementing counter with specific value."""
        metrics_collector.increment_counter(
            "test_counter",
            category=MetricCategory.EXECUTION,
            value=5.0
        )

        metrics = metrics_collector.get_metrics("test_counter")
        assert metrics[0].value == 5.0

    def test_increment_counter_with_labels(self, metrics_collector):
        """Test incrementing counter with labels."""
        metrics_collector.increment_counter(
            "test_counter",
            category=MetricCategory.EXECUTION,
            labels={"env": "test", "component": "api"}
        )

        metrics = metrics_collector.get_metrics("test_counter")
        assert metrics[0].labels == {"env": "test", "component": "api"}

    def test_set_gauge(self, metrics_collector):
        """Test setting a gauge metric."""
        metrics_collector.set_gauge(
            "test_gauge",
            value=42.0,
            category=MetricCategory.RESOURCE
        )

        metrics = metrics_collector.get_metrics("test_gauge")
        assert len(metrics) == 1
        assert metrics[0].value == 42.0

    def test_update_gauge(self, metrics_collector):
        """Test updating an existing gauge metric."""
        metrics_collector.set_gauge("test_gauge", value=10.0, category=MetricCategory.RESOURCE)
        metrics_collector.set_gauge("test_gauge", value=20.0, category=MetricCategory.RESOURCE)

        metrics = metrics_collector.get_metrics("test_gauge")
        assert len(metrics) == 2
        assert metrics[0].value == 10.0
        assert metrics[1].value == 20.0

    def test_record_timing(self, metrics_collector):
        """Test recording a timing metric."""
        with metrics_collector.record_timing("test_timer", category=MetricCategory.PERFORMANCE):
            time.sleep(0.01)

        metrics = metrics_collector.get_metrics("test_timer")
        assert len(metrics) == 1
        assert metrics[0].value > 0.0  # Should be positive (elapsed time)

    def test_record_timing_with_labels(self, metrics_collector):
        """Test recording timing with labels."""
        with metrics_collector.record_timing(
            "test_timer",
            category=MetricCategory.PERFORMANCE,
            labels={"operation": "query"}
        ):
            time.sleep(0.01)

        metrics = metrics_collector.get_metrics("test_timer")
        assert metrics[0].labels == {"operation": "query"}

    def test_record_histogram(self, metrics_collector):
        """Test recording histogram metric."""
        metrics_collector.record_histogram(
            "test_histogram",
            value=50.0,
            category=MetricCategory.PERFORMANCE
        )

        histogram = metrics_collector.histograms.get("test_histogram")
        assert histogram is not None
        assert histogram.count == 1
        assert histogram.sum == 50.0

    def test_record_histogram_multiple_values(self, metrics_collector):
        """Test recording multiple values in histogram."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            metrics_collector.record_histogram(
                "test_histogram",
                value=value,
                category=MetricCategory.PERFORMANCE
            )

        histogram = metrics_collector.histograms.get("test_histogram")
        assert histogram.count == 5
        assert histogram.sum == sum(values)

    def test_get_all_metrics(self, metrics_collector):
        """Test getting all metrics."""
        metrics_collector.increment_counter("counter1", category=MetricCategory.EXECUTION)
        metrics_collector.set_gauge("gauge1", value=100.0, category=MetricCategory.RESOURCE)
        metrics_collector.increment_counter("counter2", category=MetricCategory.SUCCESS)

        all_metrics = metrics_collector.get_all_metrics()

        assert len(all_metrics) == 3

    def test_get_metrics_by_name(self, metrics_collector):
        """Test getting metrics by name."""
        metrics_collector.increment_counter("test_counter", category=MetricCategory.EXECUTION)
        metrics_collector.increment_counter("test_counter", category=MetricCategory.EXECUTION)
        metrics_collector.set_gauge("other_gauge", value=50.0, category=MetricCategory.RESOURCE)

        metrics = metrics_collector.get_metrics("test_counter")

        assert len(metrics) == 2
        for metric in metrics:
            assert metric.name == "test_counter"

    def test_get_metrics_by_category(self, metrics_collector):
        """Test getting metrics by category."""
        metrics_collector.increment_counter("counter1", category=MetricCategory.EXECUTION)
        metrics_collector.set_gauge("gauge1", value=100.0, category=MetricCategory.RESOURCE)
        metrics_collector.increment_counter("counter2", category=MetricCategory.EXECUTION)

        execution_metrics = metrics_collector.get_metrics_by_category(MetricCategory.EXECUTION)

        assert len(execution_metrics) == 2
        for metric in execution_metrics:
            assert metric.category == MetricCategory.EXECUTION

    def test_clear_metrics(self, metrics_collector):
        """Test clearing all metrics."""
        metrics_collector.increment_counter("counter1", category=MetricCategory.EXECUTION)
        metrics_collector.set_gauge("gauge1", value=100.0, category=MetricCategory.RESOURCE)

        assert len(metrics_collector.get_all_metrics()) == 2

        metrics_collector.clear_metrics()

        assert len(metrics_collector.get_all_metrics()) == 0

    def test_clear_metrics_by_name(self, metrics_collector):
        """Test clearing metrics by name."""
        metrics_collector.increment_counter("counter1", category=MetricCategory.EXECUTION)
        metrics_collector.set_gauge("gauge1", value=100.0, category=MetricCategory.RESOURCE)
        metrics_collector.increment_counter("counter2", category=MetricCategory.EXECUTION)

        metrics_collector.clear_metrics_by_name("counter1")

        assert metrics_collector.get_metrics("counter1") == []
        assert len(metrics_collector.get_metrics("counter2")) == 1

    def test_export_metrics(self, metrics_collector, temp_dir):
        """Test exporting metrics to file."""
        metrics_collector.increment_counter("counter1", category=MetricCategory.EXECUTION)
        metrics_collector.set_gauge("gauge1", value=100.0, category=MetricCategory.RESOURCE)

        export_file = temp_dir / "metrics_export.json"
        metrics_collector.export_metrics(export_file)

        assert export_file.exists()

        with open(export_file, 'r') as f:
            exported_data = json.load(f)

        assert "metrics" in exported_data
        assert "histograms" in exported_data
        assert len(exported_data["metrics"]) == 2

    def test_import_metrics(self, metrics_collector, temp_dir):
        """Test importing metrics from file."""
        import_data = {
            "metrics": [
                {
                    "name": "imported_counter",
                    "type": "counter",
                    "category": "execution",
                    "value": 10.0,
                    "timestamp": time.time(),
                    "labels": {},
                    "metadata": {}
                }
            ],
            "histograms": []
        }

        import_file = temp_dir / "metrics_import.json"
        with open(import_file, 'w') as f:
            json.dump(import_data, f)

        metrics_collector.import_metrics(import_file)

        metrics = metrics_collector.get_metrics("imported_counter")
        assert len(metrics) == 1
        assert metrics[0].value == 10.0

    def test_get_metric_summary(self, metrics_collector):
        """Test getting metric summary."""
        metrics_collector.increment_counter("counter1", category=MetricCategory.EXECUTION)
        metrics_collector.increment_counter("counter1", category=MetricCategory.EXECUTION)
        metrics_collector.set_gauge("gauge1", value=100.0, category=MetricCategory.RESOURCE)

        summary = metrics_collector.get_metric_summary()

        assert "total_metrics" in summary
        assert "total_histograms" in summary
        assert "by_type" in summary
        assert "by_category" in summary
        assert summary["total_metrics"] == 3

    def test_record_error(self, metrics_collector):
        """Test recording an error metric."""
        metrics_collector.record_error(
            "test_error",
            error_type="ValueError",
            category=MetricCategory.ERROR
        )

        metrics = metrics_collector.get_metrics("test_error")
        assert len(metrics) == 1
        assert metrics[0].labels.get("error_type") == "ValueError"

    def test_record_success(self, metrics_collector):
        """Test recording a success metric."""
        metrics_collector.record_success(
            "test_success",
            operation="data_processing",
            category=MetricCategory.SUCCESS
        )

        metrics = metrics_collector.get_metrics("test_success")
        assert len(metrics) == 1
        assert metrics[0].labels.get("operation") == "data_processing"

    def test_record_performance(self, metrics_collector):
        """Test recording a performance metric."""
        metrics_collector.record_performance(
            "test_performance",
            operation="query",
            duration_ms=150.0,
            category=MetricCategory.PERFORMANCE
        )

        metrics = metrics_collector.get_metrics("test_performance")
        assert len(metrics) == 1
        assert metrics[0].value == 150.0
        assert metrics[0].labels.get("operation") == "query"

    def test_get_histogram_statistics(self, metrics_collector):
        """Test getting histogram statistics."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            metrics_collector.record_histogram(
                "test_histogram",
                value=value,
                category=MetricCategory.PERFORMANCE
            )

        stats = metrics_collector.get_histogram_statistics("test_histogram")

        assert "count" in stats
        assert "sum" in stats
        assert "average" in stats
        assert "min" in stats
        assert "max" in stats
        assert stats["count"] == 5
        assert stats["sum"] == sum(values)

    def test_timer_decorator(self, metrics_collector):
        """Test using timer as decorator."""
        @metrics_collector.timer("decorated_timer", category=MetricCategory.PERFORMANCE)
        def test_function():
            time.sleep(0.01)
            return "result"

        result = test_function()

        assert result == "result"
        metrics = metrics_collector.get_metrics("decorated_timer")
        assert len(metrics) == 1
        assert metrics[0].value > 0.0

    def test_counter_decorator(self, metrics_collector):
        """Test using counter as decorator."""
        @metrics_collector.counter("decorated_counter", category=MetricCategory.EXECUTION)
        def test_function():
            return "result"

        result = test_function()

        assert result == "result"
        metrics = metrics_collector.get_metrics("decorated_counter")
        assert len(metrics) == 1
        assert metrics[0].value == 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])