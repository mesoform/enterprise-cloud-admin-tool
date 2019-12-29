from datetime import datetime
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
                "successful": {"metric_type": Counter, "value_type": int, "value": None,
                               "unit": None},
                "failed": {"metric_type": Counter, "value_type": int, "value": None,
                           "unit": None}
            },
            "config": {
                "time": {"metric_type": Gauge, "value_type": float, "value": None,
                         "unit": "seconds"},
                "total": {"metric_type": Counter, "value_type": int, "value": None,
                          "unit": None},
                "successful": {"metric_type": Counter, "value_type": int, "value": None,
                               "unit": None},
                "failed": {"metric_type": Counter, "value_type": int, "value": None,
                           "unit": None}
            },
            "check": {
                "time": {"metric_type": Gauge, "value_type": float, "value": None,
                         "unit": "seconds"},
                "total": {"metric_type": Counter, "value_type": int, "value": None,
                          "unit": None},
                "successful": {"metric_type": Counter, "value_type": int, "value": None,
                               "unit": None},
                "failed": {"metric_type": Counter, "value_type": int, "value": None,
                           "unit": None}
            }
        }
        self.prepared_metrics = {}

    @property
    def metric_set(self) -> str:
        return self._metric_set

    @metric_set.setter
    def metric_set(self, value: str):
        self._metric_set = value

    @property
    def metrics(self):
        return self._metrics

    def add_metric(self, metric_name: str, metric_value: any):
        if metric_name not in self.metrics[self.metric_set][metric_name]:
            raise ValueError

        metric = self._metrics[self.metric_set][metric_name]

        if not isinstance(metric_value, metric["value_type"]):
            raise ValueError

        metric["value"] = metric_value

    def __getattr__(self, item):
        if item in self.metrics[self.metric_set]:
            return self.metrics[self.metric_set].get(item)

        raise AttributeError


class Metrics:
    """
    Base class for reporting backends
    """

    def __init__(self, args=None):
        self._metrics_registry = None
        self.start_time = datetime.utcnow()
        self.end_time = None

        if args is not None:
            self.process_args(args)

    def process_args(self, args):
        """
        Method for processing info, that came from cli, such as
        credentials data or platform-specific arguments
        """
        raise NotImplementedError

    @property
    def metrics_registry(self):
        return self._metrics_registry

    @metrics_registry.setter
    def metrics_registry(self, metric_registry: MetricsRegistry):
        self._metrics_registry = metric_registry
        self.prepare_metric_registry(metric_registry)

    def send_metrics(self):
        raise NotImplementedError

    def prepare_metric_registry(self, metric_registry: MetricsRegistry):
        """
        Enriches MetricsRegistry.metrics content and stores it in MetricsRegistry.prepared_metrics
        """
        raise NotImplementedError

    def map_unit(self, unit):
        """
        Maps generic unit to platform-specific unit.
        """
        raise NotImplementedError

    def map_value_type(self, value_type):
        """
        Maps native python type to platform-specific type for metric value.
        """
        raise NotImplementedError

    def map_metric_type(self, metric_type):
        """
        Maps primitive metric type to platform-specific metric type.
        """
        raise NotImplementedError

    @property
    def app_runtime(self):
        return self.end_time - self.start_time
