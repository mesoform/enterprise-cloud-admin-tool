import json
import logging.config
import socket
from typing import Optional

import structlog

from settings import SETTINGS

from .base import MetricsRegistry, Metrics


class LocalMetricsError(Exception):
    """
    Represents errors for local reporter
    """


def add_hostname_and_application(logger, method_name, event_dict):
    event_dict["hostname"] = socket.gethostname()
    event_dict[
        "application"
    ] = f"{SETTINGS.APPLICATION_NAME}-{SETTINGS.APPLICATION_VERSION}"
    return event_dict


def get_logger(
    module_name: str,
    log_file=None,
    syslog=None,
    debug: bool = False,
    json_formatter: bool = False,
):
    """
    Logger setup.
    """
    logging_level = logging.DEBUG if debug else logging.INFO
    default_processor = (
        structlog.processors.JSONRenderer()
        if json_formatter
        else structlog.dev.ConsoleRenderer(colors=False)
    )

    pre_chain = [
        add_hostname_and_application,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    logger_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": default_processor,
                "foreign_pre_chain": pre_chain,
            }
        },
        "handlers": {
            "default": {
                "level": logging_level,
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": logging_level,
                "propagate": True,
            }
        },
    }

    if log_file:
        logger_config["handlers"]["file"] = {
            "level": logging_level,
            "class": "logging.handlers.WatchedFileHandler",
            "filename": log_file,
            "formatter": "default",
        }
        logger_config["loggers"][""]["handlers"].append("file")

    if syslog:
        logger_config["handlers"]["syslog"] = {
            "level": logging_level,
            "class": "logging.handlers.SysLogHandler",
            "address": syslog,
            "formatter": "default",
        }
        logger_config["loggers"][""]["handlers"].append("syslog")

    logging.config.dictConfig(logger_config)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    return logging.getLogger(module_name)


class LocalMetrics(Metrics):
    def __init__(
        self,
        module_name: str,
        log_file: Optional[str] = None,
        debug: bool = False,
    ):
        super().__init__()
        self.logger = get_logger(
            module_name=module_name,
            log_file=log_file,
            syslog=False,
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
