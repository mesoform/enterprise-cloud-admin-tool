from google.cloud.monitoring_v3 import AlertPolicyServiceClient, \
    NotificationChannelServiceClient, MetricServiceClient
from google.auth.credentials import Credentials
from datetime import datetime
# noinspection PyUnresolvedReferences
from google.cloud.monitoring_v3.types import NotificationChannel, TimeSeries

DEFAULT_MONITORING_PROJECT = 'gb-me-services'
BILLING_ALERT_PERIODS = [
    "extrapolated_2h",
    "extrapolated_4h",
    "extrapolated_1d",
    "extrapolated_7d",
    "current_period"
]
_DEFAULT_BILLING_POLICY = {
    "billing_project": "",
    "budget_amount": 10.00,
    "notifications": [
        {
            "notify": "support@mesoform.com",
            "by": "email"
        }
    ]
}


class InvalidMonitoringClientType(Exception):
    pass


class TooManyMatchingResultsError(Exception):
    pass


class AlertPolicy(AlertPolicyServiceClient):
    def __init__(self, monitoring_project: str, credentials: Credentials,
                 policy: dict):
        self._monitoring_project: str = monitoring_project
        self._policy: dict = policy
        self.credentials = credentials
        super(AlertPolicy, self).__init__(credentials=self.credentials)

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

    def get_notification_channel(self, notification: dict):
        notification_channels = NotificationChannelServiceClient(
            credentials=self.credentials
        )
        notification_channels_list = \
            notification_channels.list_notification_channels(
                self.monitoring_project_path,
                "display_name='" + notification['notify'] +
                "' AND type='" + notification['by'] +
                "' AND labels.email_address='" + notification['notify'],
            )

        assert len(notification_channels_list) <= 1
        if len(notification_channels_list) == 1:
            notification_channel = notification_channels_list[0]
            return notification_channel.name
        elif len(notification_channels_list) == 0:
            notification_channel = NotificationChannel()
            notification_channel.type = notification['by']
            notification_channel.display_name = notification['notify']
            notification_channel.description = 'Send alert notification by ' + \
                                               notification['by'] + ' to ' + \
                                               notification['notify']
            if notification['by'] == 'email':
                notification_channel.labels[
                    'email_address'] = notification['notify']
            new_channel = notification_channels.create_notification_channel(
                self.monitoring_project_path, notification_channel)
            return new_channel.name
        else:
            raise TooManyMatchingResultsError(
                str(len(notification_channels_list)) +
                'notification channels found matching:\n' +
                notification['notify'] + ' by ' + notification['by'])


class BillingAlerts(AlertPolicy):
    def __init__(self, billing_alert_policy: dict):
        self._billing_alert_policy: dict = billing_alert_policy
        self._alert_policy_template: dict = {
            "display_name": None,
            "conditions": [],
            "notifications": [],
            "documentation": {
                "content": "Link to Confluence page on billing alerts"
                           "AlertAPI Key: 12345-6789-0",
                "mimeType": "text/markdown"
            },
            "combiner": "OR"
        }
        super(BillingAlerts, self).__init__()

    @property
    def billing_alert_policy(self):
        return self._billing_alert_policy

    @billing_alert_policy.setter
    def billing_alert_policy(self, value):
        self._billing_alert_policy = value

    def get_conditions_list(self):
        conditions_list = list()
        for billing_period in BILLING_ALERT_PERIODS:
            metric_filter = "resource.type=global AND " \
                            "metric.label.time_window = '" + billing_period + \
                            "' AND metric.type = " \
                            "'custom.googleapis.com/billing/" + \
                            self.billing_alert_policy.project_id + "'"
            spend_threshold = self.billing_alert_policy.budget_amount
            condition_name = "Period: " + billing_period + ", $" + \
                             self.billing_alert_policy.budget_amount + \
                             " threshold breach"
            condition = {
                "conditionThreshold": {
                    "thresholdValue": spend_threshold,
                    "filter": metric_filter,
                    "duration": "60s",
                    "comparison": "COMPARISON_GT"
                },
                "display_name": condition_name
            }
            conditions_list.append(condition)
        return conditions_list

    def define_alert_policy(self):
        policy_name = self.billing_alert_policy.project_id + \
                      " project spend thresholds"


class Metrics(MetricServiceClient):
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
        series = TimeSeries()
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
