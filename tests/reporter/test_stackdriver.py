import calendar
import textwrap

from datetime import datetime
from unittest.mock import Mock

import pytest

from reporter.stackdriver import StackdriverMetrics

NANOS_PER_MICROSECOND = 1000


@pytest.fixture
def stackdriver_reporter(command_line_args):
    stackdriver_reporter = StackdriverMetrics(command_line_args)
    stackdriver_reporter.end_time = datetime.now()

    # mocking metric_client's methods, that accept built protobuf messages
    stackdriver_reporter.metrics_client.create_time_series = Mock()
    stackdriver_reporter.metrics_client.create_metric_descriptor = Mock()
    return stackdriver_reporter


@pytest.mark.usefixtures("google_credentials")
def test_create_time_series_generate_correct_pb2_code(
    stackdriver_reporter, metrics_registry
):
    """
    Tests, that `StackdriverMetrics._initialize_base_metrics_message` generates correct
    protobuf code of TimeSeries objects.

    Also tests, that appropriate metric client's method was called.
    """
    create_time_series = stackdriver_reporter.metrics_client.create_time_series

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
    counter_timeseries_pb2_code = textwrap.dedent(
        """\
        metric {
          type: "custom.googleapis.com/deploy/%s"
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
    )
    # fmt: on

    expected_total_timeseries = counter_timeseries_pb2_code % (
        "total",
        start_seconds,
        start_nanos,
        end_seconds,
        end_nanos,
    )
    assert total_timeseries == expected_total_timeseries

    expected_successes_timeseries = counter_timeseries_pb2_code % (
        "successes",
        start_seconds,
        start_nanos,
        end_seconds,
        end_nanos,
    )
    assert successes_timeseries == expected_successes_timeseries

    expected_failures_timeseries = counter_timeseries_pb2_code % (
        "failures",
        start_seconds,
        start_nanos,
        end_seconds,
        end_nanos,
    )
    assert failures_timeseries == expected_failures_timeseries


@pytest.mark.usefixtures("google_credentials")
def test_create_metric_descriptor_generate_correct_pb2_code(
    stackdriver_reporter, metrics_registry
):
    """
    Tests, that `StackdriverMetrics._create_metric_descriptor` method generates correct
    protobuf code, that describes metrics types.

    Also tests, that appropriate metric client's method was called.
    """
    create_metric_descriptor = (
        stackdriver_reporter.metrics_client.create_metric_descriptor
    )

    stackdriver_reporter.metrics_registry = metrics_registry
    stackdriver_reporter.send_metrics()

    time_metric_descriptor = str(
        create_metric_descriptor.mock_calls[0][2]["metric_descriptor"]
    )
    total_metric_descriptor = str(
        create_metric_descriptor.mock_calls[1][2]["metric_descriptor"]
    )
    successes_metric_descriptor = str(
        create_metric_descriptor.mock_calls[2][2]["metric_descriptor"]
    )
    failures_metric_descriptor = str(
        create_metric_descriptor.mock_calls[3][2]["metric_descriptor"]
    )

    assert time_metric_descriptor == textwrap.dedent(
        """\
        metric_kind: GAUGE
        value_type: DOUBLE
        unit: "s"
        type: "custom.googleapis.com/deploy/time"
        """
    )

    counter_metric_descriptor_pb2_code = textwrap.dedent(
        """\
        metric_kind: CUMULATIVE
        value_type: INT64
        unit: "d"
        type: "custom.googleapis.com/deploy/%s"
        """
    )

    assert total_metric_descriptor == counter_metric_descriptor_pb2_code % "total"
    assert successes_metric_descriptor == counter_metric_descriptor_pb2_code % "successes"
    assert failures_metric_descriptor == counter_metric_descriptor_pb2_code % "failures"
