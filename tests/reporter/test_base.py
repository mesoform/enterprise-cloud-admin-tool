from unittest.mock import Mock

import pytest

from reporter.base import MetricsRegistry, Metrics


@pytest.mark.parametrize(
    "metric_name, metric_value",
    (("some_random_name", 123.45), ("deployment_time", "string")),
)
def test_metric_registry_error(metric_name, metric_value):
    metrics = MetricsRegistry()
    with pytest.raises(ValueError):
        metrics.add_metric(metric_name, metric_value)


def test_metric_registry():
    metrics = MetricsRegistry()

    metrics.add_metric("deployment_time", 123.45)

    metrics.add_metric("deployments_rate", 1)

    assert metrics.metrics == {
        "deployment_time": {"type": float, "unit": "second", "value": 123.45},
        "deployments_rate": {"type": int, "unit": "hour", "value": 1},
    }

    assert metrics.deployment_time
    assert metrics.deployments_rate


def test_metrics_reporter():
    metric_registry = MetricsRegistry()
    reporter = Metrics()

    prepare_metric_registry = Mock()
    reporter.prepare_metric_registry = prepare_metric_registry

    reporter.add_metric_registry(metric_registry)

    assert reporter.metrics_registry == metric_registry
    prepare_metric_registry.assert_called_once_with(metric_registry)
