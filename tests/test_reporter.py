"""
@author: Gareth Brown
@contact: gareth@mesoform.com
@date: 2017
"""
from unittest import TestCase, TextTestRunner, TestSuite
from builder import GcpAuth
from reporter.stackdriver import Metrics
from google.cloud.monitoring_v3 import MetricServiceClient

_TEST_CREDENTIALS_FILE_PATH = 'resources/gcp_token.json'


class TestReporter(TestCase):
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


def suite():
    test_suite = TestSuite()
    test_suite.addTest(
        TestReporter('test_get_credentials_without_file_returns'))
    test_suite.addTest(
        TestReporter('test_send_metrics'))
    return test_suite


if __name__ == '__main__':
    runner = TextTestRunner(verbosity=2)
    # noinspection PyCallByClass
    runner.run(suite())

