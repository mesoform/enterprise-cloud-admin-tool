from unittest.mock import Mock

import pytest

from reporter.base import MetricsRegistry, Metrics


@pytest.mark.parametrize(
    "metric_name, metric_value, metric_extra_data",
    (
        ("some_random_name", 123.45, {"some_key": "some_value"}),
        ("deployment_time", "string", {"some_key": "some_value"}),
        ("deployment_time", 123.45, {"type": "some_value"}),
    ),
)
def test_metric_registry_error(metric_name, metric_value, metric_extra_data):
    metrics = MetricsRegistry()
    with pytest.raises(ValueError):
        metrics.add_metric(metric_name, metric_value, metric_extra_data)


def test_metric_registry():
    metrics = MetricsRegistry()

    metrics.add_metric(
        metric_name="deployment_time",
        metric_value=123.45,
        metric_extra_data={"some_key": "some_value"},
    )

    metrics.add_metric(
        metric_name="deployments_rate",
        metric_value=1,
        metric_extra_data={"some_key": "some_value"},
    )

    assert metrics.metrics == {
        "deployment_time": {
            "type": float,
            "unit": "s",
            "value": 123.45,
            "some_key": "some_value",
        },
        "deployments_rate": {
            "type": int,
            "unit": "h",
            "value": 1,
            "some_key": "some_value",
        },
    }

    assert metrics.deployment_time
    assert metrics.deployments_rate


def test_metrics_reporter():
    metric_registry = MetricsRegistry()
    reporter = Metrics()

    prepare_metric_registry = Mock()
    validate_metric_registry = Mock()

    reporter.prepare_metric_registry = prepare_metric_registry
    reporter.validate_metric_registry = validate_metric_registry

    reporter.add_metric_registry(metric_registry)

    assert reporter.metrics_registry_set == [metric_registry]
    prepare_metric_registry.assert_called_once_with(metric_registry)
    validate_metric_registry.assert_called_once_with(metric_registry)
