import pytest

from common import GcpAuth

from reporter.base import MetricsRegistry
from reporter.stackdriver import (
    StackdriverReporter,
    StackdriverReporterException,
)


@pytest.mark.usefixtures("google_credentials")
@pytest.mark.parametrize(
    "metric_registry_dict, error_message",
    [
        (
            {
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "gauge",
                "value_type": "double",
                "value": "453.77329",
            },
            'Key "metric_name" is required for stackdriver metric registry.',
        ),
        (
            {
                "metric_name": "deployment_time",
                "metric_kind": "gauge",
                "value_type": "double",
                "value": "453.77329",
            },
            'Key "labels" is required for stackdriver metric registry.',
        ),
        (
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "value_type": "double",
                "value": "453.77329",
            },
            'Key "metric_kind" is required for stackdriver metric registry.',
        ),
        (
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "gauge",
                "value": "453.77329",
            },
            'Key "value_type" is required for stackdriver metric registry.',
        ),
        (
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "gauge",
                "value_type": "double",
            },
            'Key "value" is required for stackdriver metric registry.',
        ),
        (
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "some_non_existent_kind",
                "value_type": "double",
                "value": "453.77329",
            },
            f'Wrong metric kind: "some_non_existent_kind", should be one of {list(StackdriverReporter.metric_kinds.keys())}',
        ),
        (
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "gauge",
                "value_type": "some_non_existent_type",
                "value": "453.77329",
            },
            f'Wrong value type: "some_non_existent_type", should be one of {list(StackdriverReporter.value_types.keys())}',
        ),
        (
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "gauge",
                "value_type": "double",
                "value": "453.77329",
                "unit": "some_non_existent_unit",
            },
            f'Wrong unit: "some_non_existent_unit", should be one of {StackdriverReporter.units}',
        ),
    ],
)
def test_stackdriver_reporter_validation(
    metric_registry_dict, error_message, command_line_args
):
    auth = GcpAuth()

    reporter = StackdriverReporter(
        command_line_args.monitoring_namespace, auth.credentials
    )
    with pytest.raises(StackdriverReporterException) as e:
        reporter.add_metric_registry(MetricsRegistry(metric_registry_dict))

    assert str(e.value) == error_message
