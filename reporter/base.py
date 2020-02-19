from datetime import datetime, timedelta
from prometheus_metrics_proto import Counter, Gauge


class MetricsRegistry:
    """
    Instances of this class contain original and prepared metrics data
    """

    def __init__(self, metric_set: str):
        self._metric_set = metric_set
        self._metrics = {
            "deploy": {
                "time": {"metric_type": Gauge, "value_type": float, "value": None,
                         "unit": "seconds"},
                "total": {"metric_type": Counter, "value_type": int, "value": None,
                          "unit": None},
                "successes": {"metric_type": Counter, "value_type": int, "value": None,
                              "unit": None},
                "failures": {"metric_type": Counter, "value_type": int, "value": None,
                             "unit": None}
            },
            "config": {
                "time": {"metric_type": Gauge, "value_type": float, "value": None,
                         "unit": "seconds"},
                "total": {"metric_type": Counter, "value_type": int, "value": None,
                          "unit": None},
                "successes": {"metric_type": Counter, "value_type": int, "value": None,
                              "unit": None},
                "failures": {"metric_type": Counter, "value_type": int, "value": None,
                             "unit": None}
            },
            "check": {
                "time": {"metric_type": Gauge, "value_type": float, "value": None,
                         "unit": "seconds"},
                "total": {"metric_type": Counter, "value_type": int, "value": None,
                          "unit": None},
                "successes": {"metric_type": Counter, "value_type": int, "value": None,
                              "unit": None},
                "failures": {"metric_type": Counter, "value_type": int, "value": None,
                             "unit": None}
            }
        }
        self.add_metric("total", 1)

    @property
    def metric_set(self) -> str:
        return self._metric_set

    @metric_set.setter
    def metric_set(self, value: str):
        self._metric_set = value

    @property
    def metrics(self):
        return self._metrics[self.metric_set]

    def add_metric(self, metric_name: str, metric_value: any):
        if metric_name not in self.metrics:
            raise KeyError

        metric = self.metrics[metric_name]

        if not isinstance(metric_value, metric["value_type"]):
            raise ValueError

        metric["value"] = metric_value

    def __getattr__(self, item):
        if item in self.metrics:
            return self.metrics.get(item)

        raise AttributeError


class Metrics:
    """
    Base class for reporting backends
    """

    def __init__(self, args=None):
        self._metrics_registry = None
        self.start_time = datetime.utcnow()
        self.end_time = None
        self.value_types_map = {
            int: NotImplemented,
            bool: NotImplemented,
            float: NotImplemented,
            str: NotImplemented,
        }
        self.units_map = {
            "seconds": NotImplemented,
            "minutes": NotImplemented,
            "hours": NotImplemented,
            "days": NotImplemented,
        }
        self.metric_types_map = {Gauge: NotImplemented, Counter: NotImplemented}

        if args is not None:
            self._process_args(args)

    @property
    def app_runtime(self) -> timedelta:
        return self.end_time - self.start_time

    @property
    def prepared_metrics(self) -> dict:
        return self.prepare_metrics()

    @property
    def metrics_registry(self) -> MetricsRegistry:
        return self._metrics_registry

    @metrics_registry.setter
    def metrics_registry(self, metric_registry: MetricsRegistry):
        self._metrics_registry = metric_registry

    @property
    def units_map(self) -> dict:
        return self._units_map

    @units_map.setter
    def units_map(self, values: dict):
        """
        Maps generic units stored, but unimplemented in self.units_map to platform-specific units of
        the monitoring system we're sending metrics to.
        """
        self._units_map = values

    @property
    def value_types_map(self) -> dict:
        return self._value_types_map

    @value_types_map.setter
    def value_types_map(self, values: dict):
        """
        Maps native python types stored, but unimplemented in self.value_types_map to
        platform-specific value types for the monitoring system we're sending metrics to.
        """
        self._value_types_map = values

    @property
    def metric_types_map(self):
        return self._metric_types_map

    @metric_types_map.setter
    def metric_types_map(self, values: dict):
        """
        Maps primitive metric types stored, but unimplemented in self.metric_types_map to
        platform-specific metric types for the monitoring system we're sending metrics to.
        """
        self._metric_types_map = values

    def _process_args(self, args):
        """
        Method for processing info, that came from cli, such as
        credentials data or platform-specific arguments
        """
        raise NotImplementedError

    def send_metrics(self):
        """
        Sends self.prepared_metrics to monitoring system
        :return:
        """
        raise NotImplementedError

    def prepare_metrics(self) -> dict:
        """
        Enriches MetricsRegistry.metrics content and processes data to meet requirements of
        monitoring server and stores it in self.prepared_metrics, then returns enriched metrics
        """
        raise NotImplementedError


class Logger:
    """
    Base class for logging backends
    """

    def __init__(self, args):
        self.logging_client = None

        if args is not None:
            self._process_args(args)

    def _process_args(self, args):
        """
        Method for processing info, that came from cli, such as
        credentials data or platform-specific arguments
        """
        raise NotImplementedError

    def send_message(self, message: str):
        """
        Sends given string to logging backend through client
        """
        raise NotImplementedError
