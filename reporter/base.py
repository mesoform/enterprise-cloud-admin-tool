from datetime import datetime


class MetricsRegistry:
    """
    Instances of this class contain original and prepared metrics data
    """

    def __init__(self):
        self._metrics = {
            "deployment_time": {"type": float, "value": 0, "unit": "second"},
            "deployments_rate": {"type": int, "value": 1, "unit": "hour"},
        }
        self.prepared_metrics = {}

    @property
    def metrics(self):
        return self._metrics

    def add_metric(self, metric_name, metric_value):
        if metric_name not in self._metrics:
            raise ValueError

        metric = self._metrics[metric_name]

        if not isinstance(metric_value, metric["type"]):
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

    def add_metric_registry(self, metric_registry: MetricsRegistry):
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

    def map_type(self, value_type):
        """
        Maps native python type to platform-specific type.
        """
        raise NotImplementedError
