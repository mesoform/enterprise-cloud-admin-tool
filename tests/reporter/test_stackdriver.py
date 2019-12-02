import calendar
import textwrap

from datetime import datetime
from unittest.mock import Mock

import pytest

from common import GcpAuth

from reporter.base import MetricsRegistry
from reporter.stackdriver import StackdriverMetrics, StackdriverMetricsException

NANOS_PER_MICROSECOND = 1000


@pytest.mark.usefixtures("google_credentials")
@pytest.mark.parametrize(
    "metric_registry_dict, error_message",
    [
        (
            {
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "gauge",
                "value_type": "double",
                "value": 453.77329,
            },
            'Key "metric_name" is required for stackdriver metric registry.',
        ),
        (
            {
                "metric_name": "deployment_time",
                "metric_kind": "gauge",
                "value_type": "double",
                "value": 453.77329,
            },
            'Key "labels" is required for stackdriver metric registry.',
        ),
        (
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "value_type": "double",
                "value": 453.77329,
            },
            'Key "metric_kind" is required for stackdriver metric registry.',
        ),
        (
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "gauge",
                "value": 453.77329,
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
                "value": 453.77329,
            },
            f'Wrong metric kind: "some_non_existent_kind", should be one of {list(StackdriverMetrics.metric_kinds.keys())}',
        ),
        (
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "gauge",
                "value_type": "some_non_existent_type",
                "value": 453.77329,
            },
            f'Wrong value type: "some_non_existent_type", should be one of {list(StackdriverMetrics.value_types.keys())}',
        ),
        (
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "gauge",
                "value_type": "double",
                "value": 453.77329,
                "unit": "some_non_existent_unit",
            },
            f'Wrong unit: "some_non_existent_unit", should be one of {StackdriverMetrics.units}',
        ),
    ],
)
def test_stackdriver_reporter_validation(
    metric_registry_dict, error_message, command_line_args
):
    auth = GcpAuth()

    reporter = StackdriverMetrics(
        command_line_args.monitoring_namespace, auth.credentials
    )
    with pytest.raises(StackdriverMetricsException) as e:
        reporter.add_metric_registry(MetricsRegistry(metric_registry_dict))

    assert str(e.value) == error_message


def test_stackdriver_send_metrics(command_line_args):
    """
    This test ensures, that Stackdriver reporting class constructs
    correct protobuf messages.
    """
    auth = GcpAuth()

    reporter = StackdriverMetrics(
        command_line_args.monitoring_namespace, auth.credentials
    )
    reporter.end_time = datetime.now()

    # mocking metric_client's methods, that accept built protobuf messages
    create_time_series = Mock()
    create_metric_descriptor = Mock()
    reporter.metrics_client.create_time_series = create_time_series
    reporter.metrics_client.create_metric_descriptor = create_metric_descriptor

    reporter.add_metric_registry(
        MetricsRegistry(
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "gauge",
                "value_type": "double",
                "value": 453.77329,
            }
        )
    )
    reporter.add_metric_registry(
        MetricsRegistry(
            {
                "metric_name": "deployments_rate",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "cumulative",
                "value_type": "int64",
                "value": 1,
                "unit": "h",
            }
        )
    )

    reporter.send_metrics()

    # calculating start and end time in protobuf format
    start_seconds = calendar.timegm(reporter.start_time.utctimetuple())
    start_nanos = reporter.start_time.microsecond * NANOS_PER_MICROSECOND
    end_seconds = calendar.timegm(reporter.end_time.utctimetuple())
    end_nanos = reporter.end_time.microsecond * NANOS_PER_MICROSECOND

    # retrieving protobuf messages
    time_series1 = str(create_time_series.mock_calls[0][1][1][0])
    time_series2 = str(create_time_series.mock_calls[0][1][1][1])

    # fmt: off
    expected_time_series1 = textwrap.dedent(
        """\
        metric {
          labels {
            key: "command"
            value: "deploy"
          }
          labels {
            key: "result"
            value: "success"
          }
          type: "custom.googleapis.com/deployment_time"
        }
        resource {
          type: "global"
        }
        metric_kind: GAUGE
        value_type: DOUBLE
        points {
          interval {
            end_time {
              seconds: %s
              nanos: %s
            }
          }
          value {
            double_value: 453.77329
          }
        }
        """
    ) % (end_seconds, end_nanos)
    # fmt: on

    assert time_series1 == expected_time_series1

    # fmt: off
    expected_time_series2 = textwrap.dedent(
        """\
        metric {
          labels {
            key: "command"
            value: "deploy"
          }
          labels {
            key: "result"
            value: "success"
          }
          type: "custom.googleapis.com/deployments_rate"
        }
        resource {
          type: "global"
        }
        metric_kind: CUMULATIVE
        value_type: INT64
        points {
          interval {
            start_time {
              seconds: %s
              nanos: %s
            }
            end_time {
              seconds: %s
              nanos: %s
            }
          }
          value {
            int64_value: 1
          }
        }
        """
    ) % (start_seconds, start_nanos, end_seconds, end_nanos)
    # fmt: on

    assert time_series2 == expected_time_series2

    metric_descriptor_1 = str(
        create_metric_descriptor.mock_calls[0][2]["metric_descriptor"]
    )
    metric_descriptor_2 = str(
        create_metric_descriptor.mock_calls[1][2]["metric_descriptor"]
    )

    assert metric_descriptor_1 == textwrap.dedent(
        """\
        metric_kind: GAUGE
        value_type: DOUBLE
        type: "custom.googleapis.com/deployment_time"
        """
    )

    assert metric_descriptor_2 == textwrap.dedent(
        """\
        metric_kind: CUMULATIVE
        value_type: INT64
        unit: "h"
        type: "custom.googleapis.com/deployments_rate"
        """
    )
