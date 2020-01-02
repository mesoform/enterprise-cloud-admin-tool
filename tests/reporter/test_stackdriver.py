import calendar
import textwrap

from datetime import datetime
from unittest.mock import Mock

import pytest

from reporter.base import MetricsRegistry
from reporter.stackdriver import StackdriverMetrics

NANOS_PER_MICROSECOND = 1000


@pytest.mark.usefixtures("google_credentials")
def test_stackdriver_send_metrics(command_line_args):
    """
    This test ensures, that Stackdriver reporting class constructs
    correct protobuf messages.
    """
    stackdriver_reporter = StackdriverMetrics(command_line_args)
    stackdriver_reporter.end_time = datetime.now()

    # mocking metric_client's methods, that accept built protobuf messages
    create_time_series = Mock()
    create_metric_descriptor = Mock()
    stackdriver_reporter.metrics_client.create_time_series = create_time_series
    stackdriver_reporter.metrics_client.create_metric_descriptor = create_metric_descriptor

    metrics_registry = MetricsRegistry("deploy")
    metrics_registry.add_metric("time", 453.77329)
    metrics_registry.add_metric("successes", 1)

    stackdriver_reporter.metrics_registry = metrics_registry

    stackdriver_reporter.send_metrics()

    assert metrics_registry.metrics != stackdriver_reporter.prepared_metrics

    # calculating start and end time in protobuf format
    start_seconds = calendar.timegm(stackdriver_reporter.start_time.utctimetuple())
    start_nanos = stackdriver_reporter.start_time.microsecond * NANOS_PER_MICROSECOND
    end_seconds = calendar.timegm(stackdriver_reporter.end_time.utctimetuple())
    end_nanos = stackdriver_reporter.end_time.microsecond * NANOS_PER_MICROSECOND

    # retrieving protobuf messages
    time_series1 = str(create_time_series.mock_calls[0][1][1][0])
    time_series2 = str(create_time_series.mock_calls[0][1][1][1])

    # fmt: off
    expected_time_series1 = textwrap.dedent(
        """\
        metric {
          type: "custom.googleapis.com/deploy_time"
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
          type: "custom.googleapis.com/deploy_successes"
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
        type: "custom.googleapis.com/deploy_time"
        """
    )

    assert metric_descriptor_2 == textwrap.dedent(
        """\
        metric_kind: CUMULATIVE
        value_type: INT64
        unit: "h"
        type: "custom.googleapis.com/deploy_successes"
        """
    )
