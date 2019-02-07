from google.cloud.monitoring_v3 import AlertPolicyServiceClient, \
    NotificationChannelServiceClient, MetricServiceClient
from google.auth.credentials import Credentials
from datetime import datetime
# noinspection PyUnresolvedReferences
from google.cloud.monitoring_v3.types import NotificationChannel, TimeSeries
from google.cloud.monitoring_v3.types import AlertPolicy as \
    StackdriverAlertPolicy
import json
from decimal import *

getcontext().prec = 2  # Set decimal places to two

DEFAULT_MONITORING_PROJECT = 'gb-me-services'
BILLING_ALERT_PERIODS = [
    "extrapolated_2h",
    "extrapolated_4h",
    "extrapolated_1d",
    "extrapolated_7d",
    "current_period"
]
DEFAULT_BILLING_POLICY = {
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


class MediaTypeNotSupported(Exception):
    pass


class AlertPolicy(AlertPolicyServiceClient):
    def __init__(self,
                 monitoring_project: str,
                 credentials: Credentials = None,
                 policy: dict = None):
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

    @staticmethod
    def __condition_exists(alert_policy, condition_name):
        """ to be used when updating AlertPolicy conditions"""
        for condition in alert_policy.conditions:
            if condition.display_name == condition_name:
                return True
        return False

    def get_notification_channel(
            self,
            contact: str,
            media: str,
            notification_channel_client=NotificationChannelServiceClient):

        notification_channels = notification_channel_client(
            credentials=self.credentials)

        if media == 'email':
            label = "labels.email_address='" + contact + "'"
        else:
            raise MediaTypeNotSupported(media + "is not currently supported")

        notification_channels_list = \
            list(notification_channels.list_notification_channels(
                self.monitoring_project_path,
                "display_name='" + contact +
                "' AND type='" + media +
                "' AND " + label,
            ))

        if len(notification_channels_list) > 1:
            raise TooManyMatchingResultsError(
                str(len(notification_channels_list)) +
                ' notification channels found matching:\n notify ' +
                contact + ' by ' + media)
        elif len(notification_channels_list) == 1:
            notification_channel = notification_channels_list[0]
            return notification_channel.name
        elif len(notification_channels_list) == 0:
            notification_channel = NotificationChannel()
            notification_channel.type = media
            notification_channel.display_name = contact
            notification_channel.description = 'Send alert notification by ' + \
                                               media + ' to ' + \
                                               contact
            if media == 'email':
                notification_channel.labels[
                    'email_address'] = contact
            new_channel = notification_channels.create_notification_channel(
                self.monitoring_project_path, notification_channel)
            return new_channel.name


class BillingAlert(AlertPolicy):
    def __init__(self,
                 monitoring_project: str = None,
                 monitoring_credentials: Credentials = None,
                 billing_project_id: str = None,
                 billing_threshold: float = None,
                 billing_contact_address: str = None,
                 notify_contact_by: str = None,
                 notification_channel: str = None,
                 complete_alert_policy: dict = None):

        self.credentials = monitoring_credentials
        self._monitoring_project: str = monitoring_project
        self._billing_threshold: float = billing_threshold
        self._billing_contact_address: str = billing_contact_address
        self._notify_contact_by: str = notify_contact_by
        self._billing_project_id: str = billing_project_id
        self._alert_policy_template: dict = {
            "display_name": None,
            "conditions": [],
            "notifications": [],
            "documentation": {
                "content": "Link to wiki page on billing alerts",
                "mimeType": "text/markdown"
            },
            "combiner": "OR"
        }

        if not notification_channel:
            self.notification_channel = self.get_notification_channel(
                self.billing_contact_address,
                self.notify_contact_by)
        else:
            self.notification_channel = notification_channel
        if not complete_alert_policy:
            self.complete_alert_policy = self.get_complete_alert_policy()
        else:
            self.complete_alert_policy = complete_alert_policy

        super().__init__(monitoring_project=monitoring_project,
                         credentials=self.credentials,
                         policy=self.complete_alert_policy)

    @property
    def billing_threshold(self):
        return self._billing_threshold

    @billing_threshold.setter
    def billing_threshold(self, value):
        self._billing_threshold = value

    @property
    def billing_contact_address(self):
        return self._billing_contact_address

    @billing_contact_address.setter
    def billing_contact_address(self, value):
        self._billing_contact_address = value

    @property
    def notify_contact_by(self):
        return self._notify_contact_by

    @notify_contact_by.setter
    def notify_contact_by(self, value):
        self._notify_contact_by = value

    @property
    def billing_project_id(self):
        return self._billing_project_id

    @billing_project_id.setter
    def billing_project_id(self, value):
        self._billing_project_id = value

    @classmethod
    def alert_details_from_json(cls, json_data):
        """
        Sets object attributes from a JSON serialised instance.
        String should be in the format:
        {
            "project_id": project_id,
            "monthly_spend": amount_in_dollars,
            "contact": who_to_notify,
            "contact_by": how_to_contact
        }
        :param json_data: dict or str: containing JSON format above
        :return: BillingAlert from the serialised data
        """
        if not isinstance(json_data, dict):
            json_data = json.loads(json_data)

        if 'project_id' and \
                'monthly_spend' and \
                'contact' in json_data.keys():
            billing_alert = cls(
                billing_contact_address=json_data['contact'],
                notify_contact_by=json_data['contact_by'],
                billing_threshold=json_data['monthly_spend'],
                billing_project_id=json_data['project_id']
            )
        else:
            raise KeyError

        return billing_alert

    def get_conditions(
            self,
            billing_alerting_periods: list = BILLING_ALERT_PERIODS
    ):
        """

        :param billing_project_id: str: name of the project we're monitoring
            billing on
        :param billing_threshold: float: of amount of spend we want set as our
            threshold - to 2 decimal places
        :param billing_alerting_periods: list: of strings to use as label names
            for periods where spend is calculated
        :return: list: of dictionaries defining alert conditions
        """
        conditions_list = list()

        for billing_period in billing_alerting_periods:
            metric_filter = "resource.type=global AND " \
                            "metric.label.time_window = '" + billing_period + \
                            "' AND metric.type = " \
                            "'custom.googleapis.com/billing/" + \
                            self.billing_project_id + "'"
            condition_name = "Period: " + billing_period + ", $" + \
                             str(self.billing_threshold) + \
                             " threshold breach"
            condition = {
                "conditionThreshold": {
                    "thresholdValue": self.billing_threshold,
                    "filter": metric_filter,
                    "duration": "60s",
                    "comparison": "COMPARISON_GT"
                },
                "display_name": condition_name
            }
            conditions_list.append(condition)
        return conditions_list

    def get_complete_alert_policy(
            self,
            policy_display_name: str = None,
            policy_conditions: list = None,
            policy_notification_channel: str = None):
        if not policy_display_name:
            policy_display_name = self.billing_project_id + " billing alerts"
        if not isinstance(policy_conditions, list):
            policy_conditions = self.get_conditions()
        if not policy_notification_channel:
            policy_notification_channel = self.notification_channel

        policy = self._alert_policy_template
        policy['display_name'] = policy_display_name
        policy['conditions'] = policy_conditions
        policy['notifications'] = [policy_notification_channel]
        return policy


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
