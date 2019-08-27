"""
@author: Gareth Brown
@contact: gareth@mesoform.com
@date: 2017
"""
from unittest import TestCase, TextTestRunner, TestSuite, main
from teamcity import is_running_under_teamcity
from teamcity.unittestpy import TeamcityTestRunner
from common import GcpAuth
from reporter.stackdriver import Metrics, Alert, \
    TooManyMatchingResultsError
from google.cloud.monitoring_v3 import MetricServiceClient, \
    AlertPolicyServiceClient  # NotificationChannelServiceClient
from google.cloud.monitoring_v3.types import AlertPolicy as GoogleAlertPolicy
# from google.cloud.monitoring_v3.types import NotificationChannel
from google.api_core.exceptions import InvalidArgument

_TEST_CREDENTIALS_FILE_PATH = 'resources/gcp_token.json'
_TEST_ALERT_POLICY_ID = \
    'projects/gb-me-services/alertPolicies/7522594986680907020'
_TEST_NOTIFICATION_CHANNEL_ID = \
    'projects/gb-me-services/notificationChannels/17383378584079300126'
_TEST_MONITORING_PROJECT = 'gb-me-services'
_TEST_MONITORED_PROJECT = 'gb-me-services-230515'
_TEST_BILLING_THRESHOLD = 10.20
_TEST_ALERT_NOTIFY_ADDRESS = 'support@mesoform.com'
_TEST_ALERT_NOTIFY_MEDIA = 'email'
_TEST_BILLING_ALERT_PERIODS = [
    "extrapolated_1d"
]
_EXPECTED_COMPLETE_ALERT_POLICY = {
    "display_name": _TEST_MONITORED_PROJECT,
    "conditions": [
        {'conditionThreshold': {'thresholdValue': 10.2,
                                'filter': "resource.type=global AND metric.label.time_window = 'extrapolated_1d' AND metric.type = 'custom.googleapis.com/billing/gb-me-services-230515'",
                                'duration': '60s',
                                'comparison': 'COMPARISON_GT'},
         'display_name': 'Period: extrapolated_1d, $10.2 threshold breach'}
    ],
    "notifications": [_TEST_NOTIFICATION_CHANNEL_ID],
    "documentation": {
        "content": "Link to wiki page on billing alerts",
        "mimeType": "text/markdown"
    },
    "combiner": "OR"
}


class TestReporterMetrics(TestCase):
    @classmethod
    def setUpClass(cls):
        with open(_TEST_CREDENTIALS_FILE_PATH) as f:
            cls.gcp_auth = GcpAuth(f)
        cls.client = Metrics("gb-me-services",
                             cls.gcp_auth.credentials,
                             [
                                 {
                                     "project_id": "my-project",
                                     "cost": 22.22,
                                     "time_window": "2hr"
                                 }
                             ])

    def test_client_setup(self):
        self.assertIsInstance(self.client, MetricServiceClient)

    def test_send_metrics(self):
        self.assertEqual(self.client.send_metrics(), None)


class TestReporterAlertPolicy(TestCase):
    @classmethod
    def setUpClass(cls):
        with open(_TEST_CREDENTIALS_FILE_PATH) as f:
            cls.gcp_auth = GcpAuth(f)
        cls.client = Alert(
            _TEST_MONITORING_PROJECT,
            cls.gcp_auth.credentials,
            {}
        )

        cls.policy = GoogleAlertPolicy()
        #
        #
        cls.policy.display_name = "magic alert policy"
        assert not cls.policy.HasField('documentation')
        cls.policy.documentation.content = 'link to my documentation'
        cls.policy.documentation.mime_type = 'text/markdown'
        cls.policy.combiner = cls.policy.AND
        condition1 = cls.policy.conditions.add()
        condition1.display_name = 'my magic alert policy condition 1'
        condition1.condition_threshold.threshold_value = 22.00
        condition1.condition_threshold.filter = 'resource.type=global AND metric.label.time_window = "2hr" AND metric.type = "custom.googleapis.com/billing/my-project"'
        condition1.condition_threshold.duration.seconds = 60
        condition1.condition_threshold.comparison = 1
        condition1.condition_threshold.trigger.count = 3

    def test_client_setup(self):
        self.assertIsInstance(self.client, AlertPolicyServiceClient)

    def test_list_policies_contains_id(self):
        policy_ids = list()
        policies = self.client.list_alert_policies(
            self.client.project_path(self.client.monitoring_project))
        for policy in policies:
            policy_ids.append(policy.name)

        self.assertIn(_TEST_ALERT_POLICY_ID, policy_ids)

    def test_get_notification_channel_success(self):
        channel_path = self.client.notification_name_for(
            'gareth@mesoform.com', 'email')
        self.assertRegex(
            channel_path,
            'projects/' +
            _TEST_MONITORING_PROJECT +
            '/notificationChannels/[0-9]+')

    def test_get_notification_channel_fail(self):
        self.assertRaises(TooManyMatchingResultsError,
                          self.client.notification_name_for,
                          'support@mesoform.com', 'email')

    def test_get_policy(self):
        self.assertIsInstance(
            self.client.get_alert_policy(_TEST_ALERT_POLICY_ID),
            GoogleAlertPolicy)

    def test_create_policy_fails(self):
        self.assertRaises(InvalidArgument,
                          self.client.create_alert_policy,
                          self.client.monitoring_project_path,
                          {})

    def test_create_policy_succeeds(self):
        self.assertIsInstance(
            self.client.create_alert_policy(
                self.client.monitoring_project_path,
                self.policy),
            GoogleAlertPolicy)


def suite():
    test_suite = TestSuite()
    test_suite.addTest(
        TestReporterMetrics('test_get_credentials_without_file_returns'))
    test_suite.addTest(
        TestReporterMetrics('test_send_metrics'))
    test_suite.addTest(
        TestReporterAlertPolicy('test_list_policies_contains_id'))
    return test_suite


if __name__ == '__main__':
    if is_running_under_teamcity():
        runner = TeamcityTestRunner
    else:
        runner = TextTestRunner(verbosity=2).run(suite())
    main(testRunner=runner)
