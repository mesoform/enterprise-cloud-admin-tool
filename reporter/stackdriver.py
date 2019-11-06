from datetime import datetime

from google.api.metric_pb2 import MetricDescriptor
from google.cloud.monitoring_v3 import MetricServiceClient
from google.auth.credentials import Credentials

from google.cloud.monitoring_v3.types import TimeSeries


class SerializationException(Exception):
    pass


class StackdriverModuleException(Exception):
    pass


class MessageSerializer:
    """
    Performs serialization of raw metrics data to constructed message, that
    can be taken and processed by stackdriver reporting backend.
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

    def deserialize(self, raw_data):
        self._validate_raw_data(raw_data)

        deserialized = raw_data.copy()

        deserialized["metric_kind"] = self.metric_kinds[
            deserialized["metric_kind"]
        ]
        deserialized["value_type"] = self.value_types[
            deserialized["value_type"]
        ]

        return deserialized

    def _validate_raw_data(self, raw_data):
        if not isinstance(raw_data, dict):
            raise SerializationException(
                f"Wrong data, should be dict: {raw_data}"
            )

        if raw_data["metric_kind"] not in self.metric_kinds:
            raise SerializationException(
                f"Wrong metric kind: {raw_data['metric_kind']},"
                f"should be one of {list(self.metric_kinds.keys())}"
            )

        if raw_data["value_type"] not in self.value_types:
            raise SerializationException(
                f"Wrong value type: {raw_data['value_type']},"
                f"should be one of {list(self.value_types.keys())}"
            )

        if "unit" in raw_data and raw_data["unit"] not in self.units:
            raise SerializationException(
                f"Wrong unit: {raw_data['unit']},"
                f"should be one of {self.units}"
            )

    def _is_value_valid(self, value):
        """
        Here should be some validation of raw metric data value.
        """


class Metrics(object):
    def __init__(
        self,
        monitoring_project: str,
        monitoring_credentials: Credentials,
        metrics_set_list: list = None,
        metrics_client=MetricServiceClient,
        metrics_type=TimeSeries,
        complete_message=None,
        serializer_class=MessageSerializer,
    ):
        self._monitoring_project: str = monitoring_project
        self._monitoring_credentials: Credentials = monitoring_credentials
        self._metrics_set_list: list = metrics_set_list or []
        self._metrics_client = metrics_client
        self._metrics_type = metrics_type
        self._complete_message = complete_message
        self._serializer = serializer_class()

    @property
    def complete_message(self):
        """
        Completely constructed and initialized Protobuf message for given metrics_type
        """
        return self._complete_message

    @complete_message.setter
    def complete_message(self, value):
        self._complete_message = value

    @property
    def metrics_type(self):
        return self._metrics_type

    @metrics_type.setter
    def metrics_type(self, class_):
        self._metrics_type = class_

    @property
    def metrics_client(self):
        return self._metrics_client(credentials=self.monitoring_credentials)

    @metrics_client.setter
    def metrics_client(self, class_):
        self._metrics_client = class_

    @property
    def monitoring_credentials(self):
        return self._monitoring_credentials

    @monitoring_credentials.setter
    def monitoring_credentials(self, value: str):
        self._monitoring_credentials = value

    @property
    def monitoring_project(self):
        return self._monitoring_project

    @monitoring_project.setter
    def monitoring_project(self, value: str):
        self._monitoring_project = value

    @property
    def monitoring_project_path(self):
        return self.metrics_client.project_path(self.monitoring_project)

    @property
    def metrics_set_list(self):
        """
        metrics_set_list is a list of tuples in the form of:
        (matric_name, metric_labels, value_type, metric_value)
        value type can be: int64, bool, double, string, distribution

        For example:
        ("runtime", {"type": "seconds"}, "int", 5})
        :return: list
        """
        return self._metrics_set_list

    @metrics_set_list.setter
    def metrics_set_list(self, metrics_sets: list):
        """
        takes a list of tuples in the format described above
        :param value: list of dicts
        """
        self._metrics_set_list = [
            self._serializer.deserialize(metric) for metric in metrics_sets
        ]

    def add_metric_set(self, metrics_set):
        metric_set = self._serializer.deserialize(metrics_set)
        self._metrics_set_list.append(metric_set)

    def initialize_base_metrics_message(self, metric_name, labels):
        pass

    def add_data_points_to_metric_message(self, message, data_points):
        pass

    def send_metrics(self):
        pass


class AppMetrics(Metrics):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._start_time = datetime.utcnow()
        self._end_time = None

    def initialize_base_metrics_message(
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

        series = self.metrics_type(
            metric_kind=metric_kind, value_type=value_type
        )

        series.resource.type = "global"
        series.metric.type = f"custom.googleapis.com/{metric_name}"
        series.metric.labels.update(labels)
        return series

    def add_data_points_to_metric_message(self, message: TimeSeries, value):
        """
        takes an initialized TimeSeries Protobuf message object and adds data_point_value with the
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
            raise StackdriverModuleException(
                f"Unexpected value type: {message.value_type}"
            )

        data_point = message.points.add()
        setattr(data_point.value, attribute, value)

        if self._start_time and message.metric_kind != MetricDescriptor.GAUGE:
            data_point.interval.start_time.FromDatetime(self._start_time)

        end_time = self.end_time if self.end_time else datetime.utcnow()

        data_point.interval.end_time.FromDatetime(end_time)
        return message

    def send_metrics(self):
        time_series_list = []

        for metrics_set in self.metrics_set_list:
            value = metrics_set.pop("value")

            base_metrics = self.initialize_base_metrics_message(**metrics_set)
            time_series = self.add_data_points_to_metric_message(
                base_metrics, value
            )

            time_series_list.append(time_series)

        self.metrics_client.create_time_series(
            self.monitoring_project_path, time_series_list
        )

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    def end_time(self, value):
        self._end_time = value

    @property
    def app_runtime(self):
        return self._end_time - self._start_time
