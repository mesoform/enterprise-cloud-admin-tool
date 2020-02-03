import pytest

from reporter.cloudwatch import CloudWatchMetrics


@pytest.fixture
def cloudwatch_reporter(mocker, command_line_args):
    mocker.patch("reporter.cloudwatch.boto3")
    return CloudWatchMetrics(command_line_args)


def test_send_metrics(command_line_args, cloudwatch_reporter, metrics_registry):
    """
    Tests, that send_metrics calls metrics_client.put_metric_data
    with correct data.
    """
    cloudwatch_reporter.metrics_registry = metrics_registry
    cloudwatch_reporter.send_metrics()

    cloudwatch_reporter.metrics_client.put_metric_data.assert_called_once_with(
        MetricData=[
            {
                "Dimensions": [{"Name": "metric_set", "Value": "deploy"}],
                "MetricName": "TIME",
                "Unit": "Seconds",
                "Value": metrics_registry.time["value"],
            },
            {
                "Dimensions": [{"Name": "metric_set", "Value": "deploy"}],
                "MetricName": "TOTAL",
                "Unit": "None",
                "Value": metrics_registry.total["value"],
            },
            {
                "Dimensions": [{"Name": "metric_set", "Value": "deploy"}],
                "MetricName": "SUCCESSES",
                "Unit": "None",
                "Value": metrics_registry.successes["value"],
            },
            {
                "Dimensions": [{"Name": "metric_set", "Value": "deploy"}],
                "MetricName": "FAILURES",
                "Unit": "None",
                "Value": metrics_registry.failures["value"],
            },
        ],
        Namespace=command_line_args.monitoring_namespace.upper(),
    )
