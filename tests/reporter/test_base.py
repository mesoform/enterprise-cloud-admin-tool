from unittest.mock import Mock
from prometheus_metrics_proto import Counter, Gauge
import pytest

from reporter.base import MetricsRegistry, Metrics


@pytest.mark.parametrize(
    "metric_set", "metric_name, metric_value",
    (("config", "some_random_name", 123.45), ("deploy", "time", "string")),
)
def test_metric_registry_error(metric_set, metric_name, metric_value):
    metrics = MetricsRegistry(metric_set)
    with pytest.raises(ValueError):
        metrics.add_metric(metric_name, metric_value)


def test_metric_registry():
    metrics = MetricsRegistry("deploy")

    metrics.add_metric("time", 123.45)

    metrics.add_metric("success", 1)

    assert metrics.metrics == {
        "time": {"metric_type": Gauge, "value_type": float, "unit": "second", "value": 123.45},
        "success": {"metric_type": Counter, "value_type": int, "unit": "hour", "value": 1},
    }

    assert metrics.deployment_time
    assert metrics.deployments_rate


def test_metrics_reporter():
    metric_registry = MetricsRegistry("deploy")
    reporter = Metrics()

    prepare_metric_registry = Mock()
    reporter.prepare_metric_registry = prepare_metric_registry

    reporter.metrics_registry(metric_registry)

    assert reporter.metrics_registry == metric_registry
    prepare_metric_registry.assert_called_once_with(metric_registry)
