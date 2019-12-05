from datetime import datetime


class MetricsRegistry:
    """
    Instances of this class contain original and prepared metrics data
    """

    def __init__(self, record):
        if not isinstance(record, dict):
            raise ValueError(
                "Record passed to MetricRegistry should be type of dict."
            )

        self._raw_record = record
        self.prepared_record = {}

    @property
    def raw_record(self):
        return self._raw_record


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
