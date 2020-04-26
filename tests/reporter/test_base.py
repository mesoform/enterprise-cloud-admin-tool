from prometheus_metrics_proto import Counter, Gauge
import pytest

from reporter.base import MetricsRegistry


@pytest.mark.parametrize(
    "metric_set, metric_name, metric_value",
    (("config", "some_random_name", 123.45), ("deploy", 1, 1))
)
def test_metric_registry_raises_key_error(metric_set, metric_name, metric_value):
    """
    tests that when we pass in incorrect keys for our metric_name, we receive a KeyError
    """
    metrics = MetricsRegistry(metric_set)
    with pytest.raises(KeyError):
        metrics.add_metric(metric_name, metric_value)


@pytest.mark.parametrize(
    "metric_set, metric_name, metric_value",
    (("config", "time", 123), ("deploy", "successes", "string"))
)
def test_metric_registry_raises_value_error(metric_set, metric_name, metric_value):
    """
    tests that when we pass in incorrect values for our metric, we receive a ValueError
    """
    metrics = MetricsRegistry(metric_set)
    with pytest.raises(ValueError):
        metrics.add_metric(metric_name, metric_value)


def test_metric_registry():
    """
    Tests to ensure that the base MetricsRegistry class handles the following:
    1. As soon as the Registry is instantiated we consider the total number of attempts to process
    `metric_set` as incremented by 1
    2. We can add a time value and verify it is the correct type
    3. We can add a `successes` value and verify it is the correct type
    4. We can return those values as attributes
    """
    deploy_registry = MetricsRegistry("deploy")

    deploy_registry.add_metric("time", 123.45)

    deploy_registry.add_metric("successes", 1)

    assert deploy_registry.metrics == {
        "time": {"metric_type": Gauge, "value_type": float, "unit": "seconds", "value": 123.45},
        "successes": {"metric_type": Counter, "value_type": int, "unit": None, "value": 1},
        "failures": {"metric_type": Counter, "value_type": int, "value": None, "unit": None},
        "total": {"metric_type": Counter, "value_type": int, "value": 1, "unit": None}
    }

    assert deploy_registry.time
    assert deploy_registry.successes
