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
    "metric_name, metric_value, metric_dict, error_message",
    [
        (
            "deployment_time",
            453.77329,
            {
                "metric_name": "deployment_time",
                "metric_kind": "gauge",
                "value_type": "double",
            },
            'Key "labels" is required for stackdriver\'s metric_extra_data.',
        ),
        (
            "deployment_time",
            453.77329,
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "value_type": "double",
            },
            'Key "metric_kind" is required for stackdriver\'s metric_extra_data.',
        ),
        (
            "deployment_time",
            453.77329,
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "gauge",
            },
            'Key "value_type" is required for stackdriver\'s metric_extra_data.',
        ),
        (
            "deployment_time",
            453.77329,
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "some_non_existent_kind",
                "value_type": "double",
            },
            f'Wrong metric kind: "some_non_existent_kind", should be one of {list(StackdriverMetrics.metric_kinds.keys())}',
        ),
        (
            "deployment_time",
            453.77329,
            {
                "metric_name": "deployment_time",
                "labels": {"result": "success", "command": "deploy"},
                "metric_kind": "gauge",
                "value_type": "some_non_existent_type",
            },
            f'Wrong value type: "some_non_existent_type", should be one of {list(StackdriverMetrics.value_types.keys())}',
        ),
    ],
)
def test_stackdriver_reporter_validation(
    metric_name, metric_value, metric_dict, error_message, command_line_args
):
    auth = GcpAuth()

    reporter = StackdriverMetrics(
        command_line_args.monitoring_namespace, auth.credentials
    )
    with pytest.raises(StackdriverMetricsException) as e:
        stackdriver_metrics = MetricsRegistry()
        stackdriver_metrics.add_metric(
            metric_name=metric_name,
            metric_value=metric_value,
            metric_extra_data=metric_dict,
        )

        reporter.add_metric_registry(stackdriver_metrics)

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

    stackdriver_metrics = MetricsRegistry()
    stackdriver_metrics.add_metric(
        metric_name="deployment_time",
        metric_value=453.77329,
        metric_extra_data={
            "labels": {"result": "success", "command": "deploy"},
            "metric_kind": "gauge",
            "value_type": "double",
        },
    )
    stackdriver_metrics.add_metric(
        metric_name="deployments_rate",
        metric_value=1,
        metric_extra_data={
            "labels": {"result": "success", "command": "deploy"},
            "metric_kind": "cumulative",
            "value_type": "int64",
        },
    )

    reporter.add_metric_registry(stackdriver_metrics)

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
        unit: "s"
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
