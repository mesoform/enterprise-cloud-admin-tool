import json

from google.cloud.monitoring_v3 import AlertPolicyServiceClient, \
    NotificationChannelServiceClient, MetricServiceClient
from google.auth.credentials import Credentials
from datetime import datetime
# noinspection PyUnresolvedReferences
from google.cloud.monitoring_v3.types import NotificationChannel, TimeSeries
from google.cloud.monitoring_v3.types import AlertPolicy as \
    StackdriverAlertPolicy

from decimal import *

from settings import Settings

settings = Settings()

getcontext().prec = 2  # Set decimal places to two


class InvalidMonitoringClientType(Exception):
    pass


class TooManyMatchingResultsError(Exception):
    pass


class MediaTypeNotSupported(Exception):
    pass


class InvalidAlertPolicyCombinerError(Exception):
    pass


class InvalidConditionComparisonError(Exception):
    pass


class Alert(object):
    def __init__(self,
                 monitoring_project: str,
                 monitoring_credentials: Credentials = None,
                 policy: dict = None,
                 alert_client=AlertPolicyServiceClient,
                 notification_channel_client=NotificationChannelServiceClient,
                 alert_policy=StackdriverAlertPolicy,
                 notify_contact_by: str = None,
                 notify_contact_address: str = None):
        self._monitoring_project: str = monitoring_project
        self._policy: dict = policy
        self.credentials = monitoring_credentials
        self._alert_client = alert_client
        self._notification_channel_client = notification_channel_client
        self._alert_policy = alert_policy
        self._notify_contact_by: str = notify_contact_by
        self._notify_contact_address: str = notify_contact_address

    @property
    def notify_contact_address(self):
        return self._notify_contact_address

    @notify_contact_address.setter
    def notify_contact_address(self, value):
        self._notify_contact_address = value

    @property
    def notify_contact_by(self):
        return self._notify_contact_by

    @notify_contact_by.setter
    def notify_contact_by(self, value):
        self._notify_contact_by = value

    @property
    def alert_policy(self):
        return self._alert_policy

    @alert_policy.setter
    def alert_policy(self, class_):
        self._alert_policy = class_

    @property
    def alert_client(self):
        return self._alert_client(credentials=self.credentials)

    @alert_client.setter
    def alert_client(self, class_):
        self._alert_client = class_

    @property
    def notification_channel_client(self):
        return self._notification_channel_client(credentials=self.credentials)

    @notification_channel_client.setter
    def notification_channel_client(self, class_):
        self._notification_channel_client = class_

    @property
    def monitoring_project(self):
        return self._monitoring_project

    @monitoring_project.setter
    def monitoring_project(self, value):
        self._monitoring_project = value

    @property
    def monitoring_project_path(self):
        return self.alert_client.project_path(self.monitoring_project)

    @property
    def policy(self):
        return self._policy

    @policy.setter
    def policy(self, value):
        self._policy = value

    @staticmethod
    def __condition_exists(alert_policy, condition_name):
        """ to be used when updating Alert conditions"""
        for condition in alert_policy.conditions:
            if condition.display_name == condition_name:
                return True
        return False

    def notification_name_for(
            self,
            contact: str,
            media: str):

        if media == 'email':
            label = "labels.email_address='" + contact + "'"
        else:
            raise MediaTypeNotSupported(media + "is not currently supported")

        notification_channels_list = \
            list(self.notification_channel_client.list_notification_channels(
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
            new_channel = self.notification_channel_client.create_notification_channel(
                self.monitoring_project_path, notification_channel)
            return new_channel.name

    @staticmethod
    def alert_policy_exists(
            display_name: str,
            monitoring_project_path: str,
            alert_policy_client: AlertPolicyServiceClient):
        """
        Checks if an alert policy already exists
        :param display_name: display name of the policy
        :param monitoring_project_path: project where the monitoring data is
        :param alert_policy_client: client for communicating with Stackdriver API
        :return: True if policy exists
        """

        alert_policy_list = list(alert_policy_client.list_alert_policies(
            monitoring_project_path,
            'display_name="' + display_name + '"'
        ))

        if len(alert_policy_list) == 0:
            return True
        return False

    def initialize_alert_policy(self,
                                display_name: str,
                                documentation: str,
                                combiner: str) -> StackdriverAlertPolicy:
        """
        Initialize a basic alert policy from base class
        :param display_name: name we want to give to the alert
        :param documentation: description of the alert
        :param combiner: how to combine multiple condition. available options are 'OR' and 'AND'
        :return: ::google.cloud.monitoring_v3.types.AlertPolicy::
        """

        assert isinstance(display_name, str)
        assert isinstance(documentation, str)
        assert isinstance(combiner, str)
        if not combiner.upper() == 'OR' and not combiner.upper() == 'AND':
            raise InvalidMonitoringClientType(str(combiner.upper()) + ' is not a valid option. '
                                                                      'Only "OR" and "AND"')
        alert_policy = self.alert_policy()
        alert_policy.display_name = display_name
        alert_policy.documentation.content = documentation
        alert_policy.documentation.mime_type = 'text/markdown'
        combiner_enum = 'self.alert_policy.' + combiner.upper()
        alert_policy.combiner = eval(combiner_enum)
        return alert_policy

    @staticmethod
    def add_alert_condition(alert_policy: StackdriverAlertPolicy,
                            type_: str,
                            display_name: str,
                            filter_: str,
                            duration: int,
                            threshold=float(),
                            comparison: int = int()):
        """
        Takes an initialized AlertPolicy and adds conditions on when to fire an alert
        :param alert_policy: Initialized AlertPolicy
        :param type_: "condition_threshold" or "condition_absent"
        :param display_name: name of the condition
        :param filter_: filter used to specify metric we want to add condition on
        :param duration: period of time to which the condition must be true before firing
        :param threshold: value to which a condition will fire when breached
        :param comparison: enumerated value of greater than (>) = 1; or less than (<) = 3
        :return: ::google.cloud.monitoring_v3.types.AlertPolicy:: with added trigger conditions
        """

        assert isinstance(alert_policy, StackdriverAlertPolicy)
        assert isinstance(display_name, str)
        assert isinstance(filter_, str)
        assert (isinstance(threshold, int) or isinstance(threshold, float))
        assert isinstance(duration, float)
        assert isinstance(comparison, int)

        condition = alert_policy.conditions.add()
        condition.display_name = display_name
        condition_type = 'condition.' + type_
        eval(condition_type).filter = filter_
        eval(condition_type).duration.seconds = duration
        if type_ == 'condition_threshold':
            eval(condition_type).threshold_value = threshold
            eval(condition_type).comparison = comparison
        return alert_policy


class AppAlert(Alert):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def create_alert_from_dict(self, profile: dict):
        """
        takes a dictionary of an alert profile and constructs a correct AlertPolicy object to be
        processed by the API
        :type profile: simplified dictionary of the AlertPolicy
        :return: fully constructed ::google.cloud.monitoring_v3.types.AlertPolicy::
        """
        assert isinstance(profile, dict)
        if profile['CONDITION_COMPARISON'].upper() == 'GT':
            profile['CONDITION_COMPARISON'] = 1
        elif profile['CONDITION_COMPARISON'].upper() == 'LT':
            profile['CONDITION_COMPARISON'] = 3
        else:
            raise InvalidConditionComparisonError

        base_policy = self.initialize_alert_policy(
            profile['NAME'],
            profile['DESCRIPTION'],
            'OR')
        initialized_policy = self.add_alert_condition(
            base_policy,
            'condition_threshold',
            profile['CONDITION_NAME'],
            profile['CONDITION_FILTER'],
            profile['CONDITION_DURATION'],
            profile['CONDITION_THRESHOLD'],
            profile['CONDITION_COMPARISON']
        )
        if 'ABSENT_CONDITION_NAME' in profile:
            initialized_policy = self.add_alert_condition(
                initialized_policy,
                'condition_absent',
                profile['ABSENT_CONDITION_NAME'],
                profile['CONDITION_FILTER'],
                profile['ABSENT_CONDITION_DURATION']
            )
        for contact in profile['NOTIFICATION_CONTACTS']:
            initialized_policy.notification_channels.append(
                self.notification_name_for(contact['ADDRESS'], contact['media']))
        return initialized_policy

    def create_alerts(self, alerts_list):
        for profile in alerts_list:
            if not self.alert_policy_exists(profile['NAME'],
                                            self.monitoring_project_path,
                                            self.alert_client):
                self.alert_client.create_alert_policy(
                    self.monitoring_project_path,
                    self.create_alert_from_dict(profile))


class BillingAlert(Alert):
    def __init__(self,
                 billing_project_id: str = None,
                 billing_threshold: float = None,
                 **kwargs):
        self._billing_threshold: float = billing_threshold
        self._billing_project_id: str = billing_project_id
        super().__init__(**kwargs)

    @property
    def billing_threshold(self):
        return self._billing_threshold

    @billing_threshold.setter
    def billing_threshold(self, value):
        self._billing_threshold = value

    @property
    def billing_project_id(self):
        return self._billing_project_id

    @billing_project_id.setter
    def billing_project_id(self, value):
        self._billing_project_id = value

    @classmethod
    def from_json(cls, json_data):
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

        if 'contact_by' not in json_data.keys():
            json_data['contact_by'] = 'email'

        return cls(
            notify_contact_address=json_data['contact'],
            notify_contact_by=json_data['contact_by'],
            billing_threshold=json_data['monthly_spend'],
            billing_project_id=json_data['project_id']
        )

    # noinspection PyDefaultArgument
    def get_conditions(
            self,
            billing_alerting_periods: list = settings.BILLING_ALERT_PERIODS
    ):
        """

        :param billing_project_id: str: name of the project we're monitoring
            billing on
        :param billing_threshold: float: of amount of spend we want set as our
            threshold - to 2 decimal places
        :param billing_alerting_periods: list: of strings to use as label names
            for periods where spend is calculated
        :type billing_alerting_periods: list
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


class Metrics(object):
    def __init__(self, monitoring_project: str,
                 monitoring_credentials: Credentials,
                 metrics_set_list: list = None,
                 metrics_client=MetricServiceClient,
                 metrics_type=TimeSeries,
                 complete_message=None):
        self._monitoring_project: str = monitoring_project
        self._monitoring_credentials: Credentials = monitoring_credentials
        self._metrics_set_list: list = metrics_set_list or []
        self._metrics_client = metrics_client
        self._metrics_type = metrics_type
        self._complete_message = complete_message

    class MissingMetricSetValue(Exception):
        pass

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

    def initialize_base_metrics_message(self, metric_name: str, labels: dict) -> TimeSeries:
        """
        creates an TimeSeries metrics object called metric_name and with labels
        :param metric_name: name to call custom metric. As in custom.googleapis.com/ + metric_name
        :param labels: metric labels to add
        :return: ::google.cloud.monitoring_v3.types.TimeSeries::
        """
        series = self.metrics_type()
        series.resource.type = 'global'
        series.metric.type = 'custom.googleapis.com/' + metric_name
        for k, v in labels.items():
            series.metric.labels[k] = v
        return series

    def add_data_points_to_metric_message(self, message: TimeSeries, data_point_value: float):
        """
        takes an initialized TimeSeries Protobuf message object and adds data_point_value with the
            end_time as now()
        :param message: TimeSeries object
        :param data_point_value: value to add
        :return: ::google.cloud.monitoring_v3.types.TimeSeries::
        """
        data_point = message.points.add()
        data_point.value.double_value = data_point_value
        data_point.interval.end_time.FromDatetime(datetime.utcnow())
        return message

    def send_metrics(self):
        time_series_list = list()
        try:
            for metrics_set in self.metrics_set_list:
                base_metrics = self.initialize_base_metrics_message(metrics_set[0], metrics_set[1])
                time_series_list.append(self.add_data_points_to_metric_message(
                    base_metrics, metrics_set[3]
                ))
        except IndexError:
            raise self.MissingMetricSetValue(
                'missing element from metric set. Needs to be tuple:'
                '(metric_name, {label_name: label_value}, metric_value)')

        self.metrics_client.create_time_series(self.monitoring_project_path, time_series_list)


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


def main():
    pass


if __name__ == '__main__':
    main()
