"""
@author: Gareth Brown
@contact: gareth@mesoform.com
@date: 2017
"""
from unittest import TestCase, TextTestRunner, TestSuite
from builder import GcpAuth
from reporter.stackdriver import Metrics, AlertPolicy
from google.cloud.monitoring_v3 import MetricServiceClient, \
    AlertPolicyServiceClient
from google.cloud.monitoring_v3.types import AlertPolicy as GoogleAlertPolicy

_TEST_CREDENTIALS_FILE_PATH = 'resources/gcp_token.json'
_TEST_ALERT_POLICY_ID = \
    'projects/gb-me-services/alertPolicies/7522594986680907020'


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
        cls.client = AlertPolicy(
            "gb-me-services",
            cls.gcp_auth.credentials)

    def test_client_setup(self):
        self.assertIsInstance(self.client, AlertPolicyServiceClient)

    def test_list_policies_contains_id(self):
        policy_ids = list()
        policies = self.client.list_alert_policies(
            self.client.project_path(self.client.monitoring_project))
        for policy in policies:
            policy_ids.append(policy.name)

        self.assertIn(_TEST_ALERT_POLICY_ID, policy_ids)

    def test_get_policy(self):
        self.assertIsInstance(
            self.client.get_alert_policy(
                'projects/gb-me-services/alertPolicies/7522594986680907020'),
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
    runner = TextTestRunner(verbosity=2)
    # noinspection PyCallByClass
    runner.run(suite())
