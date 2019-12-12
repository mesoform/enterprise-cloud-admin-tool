from time import sleep

from datetime import datetime

from time import sleep

from google.api.metric_pb2 import MetricDescriptor
from google.auth.credentials import Credentials
from google.cloud.monitoring_v3 import MetricServiceClient
from google.cloud.monitoring_v3.types import TimeSeries

from .base import MetricsRegistry, Metrics


class StackdriverMetricsException(Exception):
    """
    Represents errors for stackdriver reporter
    """


class StackdriverMetrics(Metrics):
    """
    Implementation of metrics reporter, that sends metrics to Google Stackdriver.
    """

    metric_kinds = {
        "gauge": MetricDescriptor.GAUGE,
        "cumulative": MetricDescriptor.CUMULATIVE,
    }

    value_types = {
        "int64": MetricDescriptor.INT64,
        "bool": MetricDescriptor.BOOL,
        "double": MetricDescriptor.DOUBLE,
        "string": MetricDescriptor.STRING,
        "distribution": MetricDescriptor.DISTRIBUTION,
    }

    units = ("s", "min", "h", "d")

    def __init__(
        self, monitoring_project: str, monitoring_credentials: Credentials
    ):
        super().__init__()

        self.monitoring_project: str = monitoring_project
        self.monitoring_credentials: Credentials = monitoring_credentials
        self.metrics_client = MetricServiceClient(
            credentials=self.monitoring_credentials
        )
        self.metrics_type = TimeSeries

    @property
    def monitoring_project_path(self):
        return self.metrics_client.project_path(self.monitoring_project)

    def validate_metric_registry(self, metric_registry: MetricsRegistry):
        """
        Ensures, that metrics registry contain all required data.
        """
        for metric_dict in metric_registry.metrics.values():
            for key in ("labels", "metric_kind", "value_type"):
                if key not in metric_dict:
                    raise StackdriverMetricsException(
                        f'Key "{key}" is required for stackdriver\'s metric_extra_data.'
                    )

            if metric_dict["metric_kind"] not in self.metric_kinds:
                raise StackdriverMetricsException(
                    f"Wrong metric kind: \"{metric_dict['metric_kind']}\", "
                    f"should be one of {list(self.metric_kinds.keys())}"
                )

            if metric_dict["value_type"] not in self.value_types:
                raise StackdriverMetricsException(
                    f"Wrong value type: \"{metric_dict['value_type']}\", "
                    f"should be one of {list(self.value_types.keys())}"
                )

            if "unit" in metric_dict and metric_dict["unit"] not in self.units:
                raise StackdriverMetricsException(
                    f"Wrong unit: \"{metric_dict['unit']}\", "
                    f"should be one of {self.units}"
                )

    def prepare_metric_registry(self, metric_registry: MetricsRegistry):
        """
        Fulfills `prepared_record` of metric registry with implementation-specific
        metrics data, like protobuf descriptors.
        """
        prepared_metrics = metric_registry.metrics.copy()

        for metric_dict in prepared_metrics.values():

            metric_dict["metric_kind"] = self.metric_kinds[
                metric_dict["metric_kind"]
            ]
            metric_dict["value_type"] = self.value_types[
                metric_dict["value_type"]
            ]

        metric_registry.prepared_metrics = prepared_metrics

    def _create_metric_descriptor(
        self, metric_kind, value_type, metric_name, unit
    ):
        """
        Creates metric descriptor.
        We need this because `TimeSeries` protobuf message doesn't allow to specify units, so we need
        to create metric descriptor with separate request.
        """
        metric_descriptor_values = {
            "metric_kind": metric_kind,
            "value_type": value_type,
            "type": f"custom.googleapis.com/{metric_name}",
        }
        if unit is not None:
            metric_descriptor_values["unit"] = unit

        self.metrics_client.create_metric_descriptor(
            name=self.monitoring_project_path,
            metric_descriptor=MetricDescriptor(**metric_descriptor_values),
        )

        # is we send requests through metrics_client one after another, we are receiving unclear error 500,
        # probably due to google's requests throttling
        sleep(1)

    def _initialize_base_metrics_message(
        self,
        metric_name: str,
        labels: dict,
        metric_kind=MetricDescriptor.GAUGE,
        value_type=MetricDescriptor.INT64,
        unit=None,
    ) -> TimeSeries:
        """
        creates an TimeSeries metrics object called metric_name and with labels
        :param metric_name: name to call custom metric. As in custom.googleapis.com/ + metric_name
        :param labels: metric labels to add
        :param metric_kind: the kind of measurement. It describes how the data is reported
        :param value_type: Type of metric value
        :param unit: The unit in which the metric value is reported.
        :return: ::google.cloud.monitoring_v3.types.TimeSeries::
        """
        self._create_metric_descriptor(
            metric_kind, value_type, metric_name, unit
        )

        # if we send requests through metrics_client one after another, we receive unclear error 500,
        # probably due to google's requests throttling
        sleep(1)

        series = self.metrics_type(
            metric_kind=metric_kind, value_type=value_type
        )

        series.resource.type = "global"
        series.metric.type = f"custom.googleapis.com/{metric_name}"
        series.metric.labels.update(labels)
        return series

    def _add_data_points_to_metric_message(self, message: TimeSeries, value):
        """
        Takes an initialized TimeSeries Protobuf message object and adds data_point_value with the
        end_time as now()
        :param message: TimeSeries object
        :param value: value to add to data point
        :return: ::google.cloud.monitoring_v3.types.TimeSeries::
        """
        message_value_attributes = {
            MetricDescriptor.BOOL: "bool_value",
            MetricDescriptor.INT64: "int64_value",
            MetricDescriptor.DOUBLE: "double_value",
        }
        attribute = message_value_attributes.get(message.value_type)
        if not attribute:
            raise StackdriverMetricsException(
                f"Unexpected value type: {message.value_type}"
            )

        data_point = message.points.add()
        setattr(data_point.value, attribute, value)

        if self.start_time and message.metric_kind != MetricDescriptor.GAUGE:
            data_point.interval.start_time.FromDatetime(self.start_time)

        end_time = self.end_time if self.end_time else datetime.utcnow()

        data_point.interval.end_time.FromDatetime(end_time)
        return message

    def send_metrics(self):
        """
        Constructs protobuf messages and sends them through client.
        """
        time_series_list = []

        for metrics_registry in self.metrics_registry_set:
            for metric_name, metric_dict in metrics_registry.prepared_metrics.items():
                metric_dict_copy = metric_dict.copy()

                metric_dict_copy.pop("type")
                value = metric_dict_copy.pop("value")

                base_metrics = self._initialize_base_metrics_message(
                    metric_name=metric_name, **metric_dict_copy
                )
                time_series = self._add_data_points_to_metric_message(
                    base_metrics, value
                )

                time_series_list.append(time_series)

        self.metrics_client.create_time_series(
            self.monitoring_project_path, time_series_list
        )

    @property
    def app_runtime(self):
        return self.end_time - self.start_time
