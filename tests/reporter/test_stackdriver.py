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
    ToDo: needs splitting into separate unit tests for each function, rather than all functions in
        one
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
    metrics_registry.add_metric("failures", 1)

    stackdriver_reporter.metrics_registry = metrics_registry

    stackdriver_reporter.send_metrics()

    assert metrics_registry.metrics != stackdriver_reporter.prepared_metrics

    # calculating start and end time in protobuf format
    start_seconds = calendar.timegm(stackdriver_reporter.start_time.utctimetuple())
    start_nanos = stackdriver_reporter.start_time.microsecond * NANOS_PER_MICROSECOND
    end_seconds = calendar.timegm(stackdriver_reporter.end_time.utctimetuple())
    end_nanos = stackdriver_reporter.end_time.microsecond * NANOS_PER_MICROSECOND

    # retrieving protobuf messages
    time_timeseries = str(create_time_series.mock_calls[0][1][1][0])
    total_timeseries = str(create_time_series.mock_calls[0][1][1][1])
    successes_timeseries = str(create_time_series.mock_calls[0][1][1][2])
    failures_timeseries = str(create_time_series.mock_calls[0][1][1][3])

    # fmt: off
    expected_time_timeseries = textwrap.dedent(
        """\
        metric {
          type: "custom.googleapis.com/deploy/time"
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

    assert time_timeseries == expected_time_timeseries

    # fmt: off
    expected_total_timeseries = textwrap.dedent(
        """\
        metric {
          type: "custom.googleapis.com/deploy/total"
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

    assert total_timeseries == expected_total_timeseries

    time_metric_descriptor = str(
        create_metric_descriptor.mock_calls[0][2]["metric_descriptor"]
    )
    total_metric_descriptor = str(
        create_metric_descriptor.mock_calls[1][2]["metric_descriptor"]
    )

    assert time_metric_descriptor == textwrap.dedent(
        """\
        metric_kind: GAUGE
        value_type: DOUBLE
        unit: "s"
        type: "custom.googleapis.com/deploy/time"
        """
    )

    assert total_metric_descriptor == textwrap.dedent(
        """\
        metric_kind: CUMULATIVE
        value_type: INT64
        type: "custom.googleapis.com/deploy/total"
        """
    )
