from google.cloud import monitoring_v3
from google.auth.credentials import Credentials
import time

DEFAULT_MONITORING_PROJECT = 'gb-me-services'


class InvalidMonitoringClientType(Exception):
    pass


class Alert(monitoring_v3.AlertPolicyServiceClient):
    def __init__(self, monitoring_project: str, credentials: Credentials,
                 policy: dict):
        super(Alert, self).__init__(credentials=credentials)
        self._monitoring_project = monitoring_project
        self._policy = policy

    @property
    def monitoring_project(self):
        return self._monitoring_project

    @monitoring_project.setter
    def monitoring_project(self, value):
        self._monitoring_project = value

    @property
    def policy(self):
        return self._policy

    @policy.setter
    def policy(self, value):
        self._policy = value


class Metrics(monitoring_v3.MetricServiceClient):
    def __init__(self, monitoring_project: str, credentials: Credentials,
                 metrics: dict):
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
    def metrics(self):
        return self._metrics

    @metrics.setter
    def metrics(self, value: list):
        self._metrics = value

    @staticmethod
    def __series_for(billable_project_id: str, time_window: str):
        series = monitoring_v3.types.TimeSeries()
        series.metric.type = 'custom.googleapis.com/project_spend'
        series.resource.type = 'metric'
        series.resource.labels['project_id'] = billable_project_id
        series.resource.labels['time_window'] = time_window
        return series.points.add()

    def __data_point(self, billable_project_id: str, cost: float,
                     time_window: str):
        data_point = self.__series_for(billable_project_id, time_window)
        data_point.value.double_value = cost
        now = time.time()
        data_point.interval.end_time.seconds = int(now)

    def send_metrics(self):
        for metric in self.metrics:
            project_id = metric['project_id']
            cost = metric['cost']
            time_window = metric['time_window']
            self.create_time_series(
                self.project_path(self.monitoring_project),
                self.__data_point(project_id, cost, time_window))


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
