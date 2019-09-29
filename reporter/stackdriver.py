from datetime import datetime

from google.api.metric_pb2 import MetricDescriptor
from google.cloud.monitoring_v3 import MetricServiceClient
from google.auth.credentials import Credentials

from google.cloud.monitoring_v3.types import NotificationChannel, TimeSeries


class MissingMetricSetValue(Exception):
    pass


class Metrics(object):
    def __init__(
        self,
        monitoring_project: str,
        monitoring_credentials: Credentials,
        metrics_set_list: list = None,
        metrics_client=MetricServiceClient,
        metrics_type=TimeSeries,
        complete_message=None,
    ):
        self._monitoring_project: str = monitoring_project
        self._monitoring_credentials: Credentials = monitoring_credentials
        self._metrics_set_list: list = metrics_set_list or []
        self._metrics_client = metrics_client
        self._metrics_type = metrics_type
        self._complete_message = complete_message

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
        return self._metrics_set_list

    @metrics_set_list.setter
    def metrics_set_list(self, value: list):
        self._metrics_set_list = value

    def initialize_base_metrics_message(self, metric_name, labels):
        pass

    def add_data_points_to_metric_message(self, message, data_points):
        pass

    def send_metrics(self):
        pass


class TimeSeriesMetrics(Metrics):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def initialize_base_metrics_message(
        self,
        metric_name: str,
        labels: dict,
        metric_kind=MetricDescriptor.GAUGE,
        value_type=MetricDescriptor.INT64,
    ) -> TimeSeries:
        """
        creates an TimeSeries metrics object called metric_name and with labels
        :param metric_name: name to call custom metric. As in custom.googleapis.com/ + metric_name
        :param labels: metric labels to add
        :param metric_kind: the kind of measurement. It describes how the data is reported
        :param value_type: Type of metric value
        :return: ::google.cloud.monitoring_v3.types.TimeSeries::
        """
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
        :param data_point_value: value to add
        :return: ::google.cloud.monitoring_v3.types.TimeSeries::
        """
        data_point = message.points.add()
        if message.value_type == MetricDescriptor.BOOL:
            data_point.value.bool_value = value
        elif message.value_type == MetricDescriptor.INT64:
            data_point.value.int64_value = value
        elif message.value_type == MetricDescriptor.DOUBLE:
            data_point.value.double_value = value

        data_point.interval.end_time.FromDatetime(datetime.utcnow())
        return message

    def send_metrics(self):
        time_series_list = list()
        try:
            for metrics_set in self.metrics_set_list:
                base_metrics = self.initialize_base_metrics_message(
                    metrics_set["metric_name"],
                    metrics_set["labels"],
                    metrics_set["metric_kind"],
                    metrics_set["value_type"],
                )
                time_series_list.append(
                    self.add_data_points_to_metric_message(
                        base_metrics, metrics_set["value"]
                    )
                )
        except IndexError:
            raise MissingMetricSetValue(
                "missing element from metric set. Needs to be tuple:"
                "(metric_name, {label_name: label_value}, metric_value)"
            )

        self.metrics_client.create_time_series(
            self.monitoring_project_path, time_series_list
        )


class AppMetrics(TimeSeriesMetrics):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._start_time = datetime.utcnow()
        self._end_time = None

    @property
    def end_time(self):
        return self._end_time

    @end_time.setter
    def end_time(self, value):
        self._end_time = value
