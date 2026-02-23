"""Metrics provider.

Provider that can be imported by service and runtime layers.
"""

from typing import Any

# In-memory metrics store for demo
_metrics: dict[str, list[Any]] = {}


def record_metric(name: str, value: float, **tags: str) -> None:
    """Record a metric.

    Args:
        name: Metric name
        value: Metric value
        **tags: Additional tags
    """
    if name not in _metrics:
        _metrics[name] = []
    _metrics[name].append({"value": value, "tags": tags})


def get_metrics(name: str) -> list[dict]:
    """Get recorded metrics.

    Args:
        name: Metric name

    Returns:
        List of recorded metric values
    """
    return _metrics.get(name, [])


def reset_metrics() -> None:
    """Reset all metrics (for testing)."""
    _metrics.clear()
