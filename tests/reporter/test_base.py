from unittest.mock import Mock

import pytest

from reporter.base import MetricsRegistry, MetricsReporter


def test_metric_registry():
    with pytest.raises(ValueError):
        MetricsRegistry(123)

    some_dict = {"message": "Hello"}
    metric_registry = MetricsRegistry(some_dict)

    assert metric_registry.raw_record == some_dict
    assert metric_registry.prepared_record == {}


def test_metrics_reporter():
    metric_registry = MetricsRegistry({})
    reporter = MetricsReporter()

    prepare_metric_registry = Mock()
    validate_metric_registry = Mock()

    reporter.prepare_metric_registry = prepare_metric_registry
    reporter.validate_metric_registry = validate_metric_registry

    reporter.add_metric_registry(metric_registry)

    assert reporter.metrics_registry_set == [metric_registry]
    prepare_metric_registry.assert_called_once_with(metric_registry)
    validate_metric_registry.assert_called_once_with(metric_registry)
