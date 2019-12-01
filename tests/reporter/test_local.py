import json
import os
import socket

import pytest

from reporter.base import MetricsRegistry
from reporter.local import get_logger, LocalMetricsReporter
from settings import SETTINGS


@pytest.fixture
def log_file_path(working_directory):
    log_file_path = f"{working_directory.strpath}/enterprise_cloud_admin.log"
    yield log_file_path
    os.remove(log_file_path)


def test_get_logger_stderr(capsys):
    logger = get_logger(module_name=__name__)

    logging_entry = "some random entry"
    logger.info(logging_entry)

    captured = capsys.readouterr()

    assert logging_entry in captured.err

    logger.debug(logging_entry)

    captured = capsys.readouterr()
    assert logging_entry not in captured.err


def test_get_logger_stderr_debug(capsys):
    logger = get_logger(module_name=__name__, debug=True)

    logging_entry = "some random entry"
    logger.debug(logging_entry)

    captured = capsys.readouterr()
    assert logging_entry in captured.err


def test_get_logger_stderr_json(capsys):
    logger = get_logger(module_name=__name__, debug=True, json_formatter=True)

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
        "logger": "test_local",
    }


def test_get_logger_file_json(log_file_path):
    logger = get_logger(
        module_name=__name__,
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
        "logger": "test_local",
    }


def test_local_metrics_reporter(log_file_path):
    reporter = LocalMetricsReporter(__name__, log_file=log_file_path)

    first_metric_data = {"some_random_key": "some_random_value"}
    second_metric_data = {"some_random_key1": "some_random_value1"}

    reporter.add_metric_registry(MetricsRegistry(first_metric_data))
    reporter.add_metric_registry(MetricsRegistry(second_metric_data))

    reporter.send_metrics()

    with open(log_file_path, "r") as log_file:
        log_entries = log_file.read().split("\n")

    first_entry, second_entry = log_entries[0], log_entries[1]

    first_entry = json.loads(first_entry)
    second_entry = json.loads(second_entry)

    assert json.loads(first_entry["event"]) == first_metric_data
    assert json.loads(second_entry["event"]) == second_metric_data
