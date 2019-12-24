from time import sleep

from datetime import datetime

from time import sleep

from google.api.metric_pb2 import MetricDescriptor
from google.cloud.monitoring_v3 import MetricServiceClient
from google.cloud.monitoring_v3.types import TimeSeries

from common import GcpAuth

from .base import MetricsRegistry, Metrics


class StackdriverMetricsException(Exception):
    """
    Represents errors for stackdriver reporter
    """


class StackdriverMetrics(Metrics):
    """
    Implementation of metrics reporter, that sends metrics to Google Stackdriver.
    """

    value_types = {
        int: MetricDescriptor.INT64,
        bool: MetricDescriptor.BOOL,
        float: MetricDescriptor.DOUBLE,
        str: MetricDescriptor.STRING,
    }

    units = {"second": "s", "minute": "min", "hour": "h", "day": "d"}

    metric_name_to_kind_map = {
        "deployment_time": MetricDescriptor.GAUGE,
        "deployments_rate": MetricDescriptor.CUMULATIVE,
    }

    def __init__(self, args):
        self.monitoring_credentials = None
        self.monitoring_project = None

        super().__init__(args)

        self.metrics_client = MetricServiceClient(
            credentials=self.monitoring_credentials
        )
        self.metrics_type = TimeSeries

    def process_args(self, args):
        auth = (
            GcpAuth(args.key_file)
            if getattr(args, "key_file", None)
            else GcpAuth()
        )

        self.monitoring_credentials = auth.credentials
        self.monitoring_project = args.monitoring_namespace

    @property
    def monitoring_project_path(self):
        return self.metrics_client.project_path(self.monitoring_project)

    def map_unit(self, unit):
        return self.units[unit]

    def map_type(self, value_type):
        return self.value_types[value_type]

    def prepare_metric_registry(self, metric_registry: MetricsRegistry):
        """
        Fulfills `prepared_record` of metric registry with implementation-specific
        metrics data, like protobuf descriptors.
        """
        for metric_name, metric_dict in metric_registry.metrics.items():
            prepared_metric_dict = metric_dict.copy()

            prepared_metric_dict["metric_kind"] = self.metric_name_to_kind_map[
                metric_name
            ]
            prepared_metric_dict["value_type"] = self.map_type(
                prepared_metric_dict.pop("type")
            )
            prepared_metric_dict["unit"] = self.map_unit(
                prepared_metric_dict["unit"]
            )

            metric_registry.prepared_metrics[metric_name] = prepared_metric_dict

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
        labels: dict = None,
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
        if labels:
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

        for (
            metric_name,
            metric_dict,
        ) in self.metrics_registry.prepared_metrics.items():
            metric_dict_copy = metric_dict.copy()
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
