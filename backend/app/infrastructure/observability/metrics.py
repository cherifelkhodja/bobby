"""
Metrics collection infrastructure.

Provides Prometheus-compatible metrics for monitoring.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable, Optional


@dataclass
class MetricValue:
    """Single metric value with labels."""

    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Counter:
    """
    Counter metric that can only increase.

    Example:
        requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"]
        )
        requests_total.inc(method="GET", endpoint="/api/users", status="200")
    """

    def __init__(
        self,
        name: str,
        description: str,
        labels: Optional[list[str]] = None,
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: dict[tuple, float] = defaultdict(float)
        self._lock = Lock()

    def inc(self, value: float = 1.0, **labels: str) -> None:
        """Increment the counter."""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] += value

    def _make_key(self, labels: dict[str, str]) -> tuple:
        """Create a hashable key from labels."""
        return tuple(labels.get(name, "") for name in self.label_names)

    def get_all(self) -> list[MetricValue]:
        """Get all metric values."""
        result = []
        with self._lock:
            for key, value in self._values.items():
                labels = dict(zip(self.label_names, key))
                result.append(MetricValue(value=value, labels=labels))
        return result


class Gauge:
    """
    Gauge metric that can increase or decrease.

    Example:
        active_connections = Gauge(
            "active_connections",
            "Number of active connections"
        )
        active_connections.set(42)
        active_connections.inc()
        active_connections.dec()
    """

    def __init__(
        self,
        name: str,
        description: str,
        labels: Optional[list[str]] = None,
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: dict[tuple, float] = defaultdict(float)
        self._lock = Lock()

    def set(self, value: float, **labels: str) -> None:
        """Set the gauge value."""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] = value

    def inc(self, value: float = 1.0, **labels: str) -> None:
        """Increment the gauge."""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] += value

    def dec(self, value: float = 1.0, **labels: str) -> None:
        """Decrement the gauge."""
        key = self._make_key(labels)
        with self._lock:
            self._values[key] -= value

    def _make_key(self, labels: dict[str, str]) -> tuple:
        """Create a hashable key from labels."""
        return tuple(labels.get(name, "") for name in self.label_names)

    def get_all(self) -> list[MetricValue]:
        """Get all metric values."""
        result = []
        with self._lock:
            for key, value in self._values.items():
                labels = dict(zip(self.label_names, key))
                result.append(MetricValue(value=value, labels=labels))
        return result


class Histogram:
    """
    Histogram metric for measuring distributions.

    Example:
        request_duration = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
        )
        request_duration.observe(0.123, method="GET", endpoint="/api/users")
    """

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(
        self,
        name: str,
        description: str,
        labels: Optional[list[str]] = None,
        buckets: Optional[tuple[float, ...]] = None,
    ):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._counts: dict[tuple, dict[float, int]] = defaultdict(
            lambda: {b: 0 for b in self.buckets}
        )
        self._sums: dict[tuple, float] = defaultdict(float)
        self._totals: dict[tuple, int] = defaultdict(int)
        self._lock = Lock()

    def observe(self, value: float, **labels: str) -> None:
        """Record an observation."""
        key = self._make_key(labels)
        with self._lock:
            self._sums[key] += value
            self._totals[key] += 1
            for bucket in self.buckets:
                if value <= bucket:
                    self._counts[key][bucket] += 1

    def _make_key(self, labels: dict[str, str]) -> tuple:
        """Create a hashable key from labels."""
        return tuple(labels.get(name, "") for name in self.label_names)

    def get_all(self) -> dict[str, Any]:
        """Get all histogram data."""
        result = {}
        with self._lock:
            for key in self._totals:
                labels = dict(zip(self.label_names, key))
                label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
                result[label_str] = {
                    "buckets": dict(self._counts[key]),
                    "sum": self._sums[key],
                    "count": self._totals[key],
                }
        return result


class MetricsCollector:
    """
    Central metrics collector.

    Manages all application metrics and provides export functionality.

    Example:
        metrics = MetricsCollector()

        # Register metrics
        http_requests = metrics.counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "status"]
        )

        # Use metrics
        http_requests.inc(method="GET", status="200")

        # Export
        print(metrics.export_prometheus())
    """

    def __init__(self):
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._lock = Lock()

    def counter(
        self,
        name: str,
        description: str,
        labels: Optional[list[str]] = None,
    ) -> Counter:
        """Create or get a counter metric."""
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, description, labels)
            return self._counters[name]

    def gauge(
        self,
        name: str,
        description: str,
        labels: Optional[list[str]] = None,
    ) -> Gauge:
        """Create or get a gauge metric."""
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, description, labels)
            return self._gauges[name]

    def histogram(
        self,
        name: str,
        description: str,
        labels: Optional[list[str]] = None,
        buckets: Optional[tuple[float, ...]] = None,
    ) -> Histogram:
        """Create or get a histogram metric."""
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, description, labels, buckets)
            return self._histograms[name]

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus format."""
        lines = []

        # Export counters
        for name, counter in self._counters.items():
            lines.append(f"# HELP {name} {counter.description}")
            lines.append(f"# TYPE {name} counter")
            for mv in counter.get_all():
                label_str = ",".join(f'{k}="{v}"' for k, v in mv.labels.items())
                if label_str:
                    lines.append(f"{name}{{{label_str}}} {mv.value}")
                else:
                    lines.append(f"{name} {mv.value}")

        # Export gauges
        for name, gauge in self._gauges.items():
            lines.append(f"# HELP {name} {gauge.description}")
            lines.append(f"# TYPE {name} gauge")
            for mv in gauge.get_all():
                label_str = ",".join(f'{k}="{v}"' for k, v in mv.labels.items())
                if label_str:
                    lines.append(f"{name}{{{label_str}}} {mv.value}")
                else:
                    lines.append(f"{name} {mv.value}")

        # Export histograms
        for name, hist in self._histograms.items():
            lines.append(f"# HELP {name} {hist.description}")
            lines.append(f"# TYPE {name} histogram")
            for label_str, data in hist.get_all().items():
                base_labels = f"{{{label_str}}}" if label_str else ""
                for bucket, count in data["buckets"].items():
                    bucket_labels = f'le="{bucket}"'
                    if label_str:
                        bucket_labels = f"{label_str},{bucket_labels}"
                    lines.append(f"{name}_bucket{{{bucket_labels}}} {count}")
                lines.append(f"{name}_sum{base_labels} {data['sum']}")
                lines.append(f"{name}_count{base_labels} {data['count']}")

        return "\n".join(lines)

    def export_json(self) -> dict[str, Any]:
        """Export all metrics as JSON."""
        return {
            "counters": {
                name: [
                    {"value": mv.value, "labels": mv.labels}
                    for mv in counter.get_all()
                ]
                for name, counter in self._counters.items()
            },
            "gauges": {
                name: [
                    {"value": mv.value, "labels": mv.labels}
                    for mv in gauge.get_all()
                ]
                for name, gauge in self._gauges.items()
            },
            "histograms": {
                name: hist.get_all() for name, hist in self._histograms.items()
            },
        }


# Global metrics instance
metrics = MetricsCollector()

# Pre-defined application metrics
http_requests_total = metrics.counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = metrics.histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

active_connections = metrics.gauge(
    "active_connections",
    "Number of active connections",
)

database_queries_total = metrics.counter(
    "database_queries_total",
    "Total database queries",
    ["operation", "table"],
)

cache_hits_total = metrics.counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_name"],
)

cache_misses_total = metrics.counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_name"],
)

cooptations_total = metrics.counter(
    "cooptations_total",
    "Total cooptations submitted",
    ["status"],
)

auth_attempts_total = metrics.counter(
    "auth_attempts_total",
    "Total authentication attempts",
    ["result"],
)
