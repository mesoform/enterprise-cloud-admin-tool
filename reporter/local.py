import json
import logging.config
import logging.handlers
import socket
from typing import Optional

import structlog

from settings import SETTINGS

from .base import MetricsRegistry, Metrics

APPLICATION = f"{SETTINGS.APPLICATION_NAME}-{SETTINGS.APPLICATION_VERSION}"


class LocalMetricsError(Exception):
    """
    Represents errors for local reporter
    """


class ContextFilter(logging.Filter):
    """
    Context filter for basic formatter.
    """

    def filter(self, record):
        record.hostname = socket.gethostname()
        record.application = APPLICATION
        return True


def _add_hostname_and_application(logger, method_name, event_dict):
    event_dict["hostname"] = socket.gethostname()
    event_dict["application"] = APPLICATION
    return event_dict


_JSON_FORMATTER = structlog.stdlib.ProcessorFormatter(
    processor=structlog.processors.JSONRenderer(),
    foreign_pre_chain=[
        _add_hostname_and_application,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ],
)

_BASIC_FORMATTER = logging.Formatter(
    "%(asctime)s [%(application)s] [%(threadName)s] [%(name)s] %(levelname)s: %(message)s"
)


def get_logger(
    module_name: str,
    log_file: str = None,
    syslog: str = None,
    stream_logger: bool = True,
    debug: bool = False,
    json_formatter: bool = False,
) -> logging.Logger:
    """
    Helper method, that allows to setup logger instance with arbitrary combination of logging
    handlers.
    Also, allows to format all logs in json format. For this, we use `ProcessorFormatter` from
    structlog package.

    :param module_name: name of module, where get_logger will be used
    :param log_file: path to file, enables logging to file
    :param syslog: syslog address, enables logging to syslog
    :param stream_logger: enables logging to standard output
    :param debug: enables debug logging level
    :param json_formatter: formats logs in json
    """
    logger = logging.getLogger(module_name)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.handlers = []

    formatter = _JSON_FORMATTER if json_formatter else _BASIC_FORMATTER
    if not json_formatter:
        logger.addFilter(ContextFilter())

    if stream_logger:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if syslog:
        syslog_handler = logging.handlers.SysLogHandler(syslog)
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)

    return logger


class LocalMetrics(Metrics):
    def __init__(
        self,
        module_name: str,
        metrics_file: Optional[str] = None,
        debug: bool = False,
    ):
        super().__init__()
        self.logger = get_logger(
            module_name=module_name,
            log_file=metrics_file,
            debug=debug,
            json_formatter=True,
        )

    def send_metrics(self):
        for metrics_registry in self.metrics_registry_set:
            self.logger.info(metrics_registry.prepared_record)

    def validate_metric_registry(self, metric_registry: MetricsRegistry):
        """
        For local metrics reporting we don't need any validation.
        """

    def prepare_metric_registry(self, metric_registry: MetricsRegistry):
        metric_registry.prepared_record = json.dumps(metric_registry.raw_record)
