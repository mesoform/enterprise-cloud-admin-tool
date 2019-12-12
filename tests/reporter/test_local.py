import json
import os
import socket

from uuid import uuid4

import pytest

from reporter.base import MetricsRegistry
from reporter.local import get_logger, LocalMetrics
from settings import SETTINGS


@pytest.fixture
def log_file_path(working_directory):
    log_file_path = f"{working_directory.strpath}/enterprise_cloud_admin.log"

    try:
        os.remove(log_file_path)
    except FileNotFoundError:
        pass

    yield log_file_path

    try:
        os.remove(log_file_path)
    except FileNotFoundError:
        pass


def test_get_logger_stderr(capsys):
    logger = get_logger(module_name=str(uuid4()))

    logging_entry = "some random entry"
    logger.info(logging_entry)

    captured = capsys.readouterr()

    assert logging_entry in captured.err

    logger.debug(logging_entry)

    captured = capsys.readouterr()
    assert logging_entry not in captured.err


def test_get_logger_stderr_debug(capsys):
    logger = get_logger(module_name=str(uuid4()), debug=True)

    logging_entry = "some random entry"
    logger.debug(logging_entry)

    captured = capsys.readouterr()
    assert logging_entry in captured.err


def test_get_logger_stderr_json(capsys):
    module_name = str(uuid4())
    logger = get_logger(
        module_name=module_name, debug=True, json_formatter=True
    )

    logging_entry = "some random entry"
    logger.debug(logging_entry)

    captured = capsys.readouterr()

    result = json.loads(captured.err)

    assert result.pop("timestamp")

    assert result == {
        "application": f"{SETTINGS.APPLICATION_NAME}-{SETTINGS.APPLICATION_VERSION}",
        "event": "some random entry",
        "hostname": socket.gethostname(),
        "level": "debug",
        "logger": module_name,
    }


def test_get_logger_file_json(log_file_path):
    module_name = str(uuid4())
    logger = get_logger(
        module_name=module_name,
        log_file=log_file_path,
        debug=True,
        json_formatter=True,
    )

    logging_entry = "some random entry"
    logger.debug(logging_entry)

    with open(log_file_path, "r") as log_file:
        result = json.loads(log_file.read())

    assert result.pop("timestamp")

    assert result == {
        "application": f"{SETTINGS.APPLICATION_NAME}-{SETTINGS.APPLICATION_VERSION}",
        "event": "some random entry",
        "hostname": socket.gethostname(),
        "level": "debug",
        "logger": module_name,
    }


def test_local_metrics_reporter(log_file_path):
    reporter = LocalMetrics(metrics_file=log_file_path)

    first_metric_data = {"some_random_key": "some_random_value"}
    second_metric_data = {"some_random_key1": "some_random_value1"}

    metrics = MetricsRegistry()
    metrics.add_metric(
        metric_name="deployment_time",
        metric_value=123.34,
        metric_extra_data=first_metric_data,
    )
    metrics.add_metric(
        metric_name="deployments_rate",
        metric_value=1,
        metric_extra_data=second_metric_data,
    )

    reporter.add_metric_registry(metrics)
    reporter.send_metrics()

    with open(log_file_path, "r") as log_file:
        log_entries = log_file.read().split("\n")

    log_entries.sort()

    first_entry, second_entry = log_entries[1], log_entries[2]

    assert json.loads(first_entry) == {
        **first_metric_data,
        **{
            "metric_name": "deployment_time",
            "value": 123.34,
            "type": "float",
            "unit": "s",
        },
    }

    assert json.loads(second_entry) == {
        **second_metric_data,
        **{
            "metric_name": "deployments_rate",
            "value": 1,
            "type": "int",
            "unit": "h",
        },
    }
