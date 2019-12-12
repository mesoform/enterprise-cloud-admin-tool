from datetime import datetime


class MetricsRegistry:
    """
    Instances of this class contain original and prepared metrics data
    """

    METRICS_TEMPLATES = {
        "deployment_time": {"type": float, "value": 0, "unit": "s"},
        "deployments_rate": {"type": int, "value": 1, "unit": "h"},
    }

    def __init__(self):
        self._metrics = {}
        self.prepared_metrics = {}

    @property
    def metrics(self):
        return self._metrics

    def add_metric(self, metric_name, metric_value, metric_extra_data=None):
        if metric_name not in self.METRICS_TEMPLATES:
            raise ValueError

        template = self.METRICS_TEMPLATES[metric_name]

        if not isinstance(metric_value, template["type"]):
            raise ValueError

        metric = self._metrics.setdefault(metric_name, {})

        metric["type"] = template["type"]
        metric["unit"] = template["unit"]

        metric["value"] = metric_value

        if metric_extra_data is not None:
            if {"type", "unit", "value"} & set(metric_extra_data.keys()):
                raise ValueError(
                    "metric_extra_data keys shouldn't intersect with 'type', 'unit' or 'value'"
                )
            metric.update(metric_extra_data)

    def __getattr__(self, item):
        if item in self.METRICS_TEMPLATES:
            return self.metrics.get(item)

        raise AttributeError


class Metrics:
    """
    Base class for reporting backends
    """

    def __init__(self, *args, **kwargs):
        self.metrics_registry_set = []

        self.start_time = datetime.utcnow()
        self.end_time = None

    def add_metric_registry(self, metric_registry: MetricsRegistry):
        self.validate_metric_registry(metric_registry)
        self.prepare_metric_registry(metric_registry)
        self.metrics_registry_set.append(metric_registry)

    def send_metrics(self):
        raise NotImplementedError

    def prepare_metric_registry(self, metric_registry: MetricsRegistry):
        raise NotImplementedError

    def validate_metric_registry(self, metric_registry: MetricsRegistry):
        raise NotImplementedError
