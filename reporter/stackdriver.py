from google.cloud import monitoring_v3
from google.auth.credentials import Credentials
from datetime import datetime

DEFAULT_MONITORING_PROJECT = 'gb-me-services'


class InvalidMonitoringClientType(Exception):
    pass


class AlertPolicy(monitoring_v3.AlertPolicyServiceClient):
    def __init__(self, monitoring_project: str, credentials: Credentials,
                 policy: dict):
        super(AlertPolicy, self).__init__(credentials=credentials)
        self._monitoring_project: str = monitoring_project
        self._policy: dict = policy

    @property
    def monitoring_project(self):
        return self._monitoring_project

    @monitoring_project.setter
    def monitoring_project(self, value):
        self._monitoring_project = value

    @property
    def monitoring_project_path(self):
        return self.project_path(self.monitoring_project)

    @property
    def policy(self):
        return self._policy

    @policy.setter
    def policy(self, value):
        self._policy = value


class Metrics(monitoring_v3.MetricServiceClient):
    def __init__(self, monitoring_project: str, credentials: Credentials,
                 metrics: list):
        super(Metrics, self).__init__(credentials=credentials)
        self._monitoring_project: str = monitoring_project
        self._metrics: list = metrics

    @property
    def monitoring_project(self):
        return self._monitoring_project

    @monitoring_project.setter
    def monitoring_project(self, value: str):
        self._monitoring_project = value

    @property
    def monitoring_project_path(self):
        return self.project_path(self.monitoring_project)

    @property
    def metrics(self):
        return self._metrics

    @metrics.setter
    def metrics(self, value: list):
        self._metrics = value

    def __series_for(self, billable_project_id: str, time_window: str):
        series = monitoring_v3.types.TimeSeries()
        series.metric.type = 'custom.googleapis.com/billing/project_spend'
        series.resource.type = 'global'
        series.metric.labels['project_id'] = billable_project_id
        series.metric.labels['time_window'] = time_window
        return series

    def __data_point(self, billable_project_id: str, cost: float,
                     time_window: str):
        series = self.__series_for(billable_project_id, time_window)
        data_point = series.points.add()
        data_point.value.double_value = cost
        data_point.interval.end_time.FromDatetime(datetime.utcnow())
        return series

    def send_metrics(self):
        data_series_set: list = []
        for metric in self.metrics:
            project_id = metric['project_id']
            cost = metric['cost']
            time_window = metric['time_window']
            data_series = self.__data_point(project_id, cost, time_window)
            data_series_set.append(data_series)

        return self.create_time_series(self.monitoring_project_path,
                                       data_series_set)


def create_alert():
    pass


def delete_alert():
    pass


def delete_metric():
    pass


def main():
    pass


if __name__ == '__main__':
    main()
