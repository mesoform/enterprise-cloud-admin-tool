"""
@author: Gareth Brown
@contact: gareth@mesoform.com
@date: 2017
"""
from unittest import TestCase, TextTestRunner, TestSuite, main
from builder import GcpAuth
from google.auth import credentials
from os import environ
from teamcity import is_running_under_teamcity
from teamcity.unittestpy import TeamcityTestRunner

_TEST_CREDENTIALS_FILE_PATH = 'resources/gcp_token.json'


class TestGetCredentials(TestCase):
    def test_get_credentials_from_file_returns(self):
        with open(_TEST_CREDENTIALS_FILE_PATH) as f:
            gcp_auth = GcpAuth(f)
        self.assertIsInstance(gcp_auth.credentials, credentials.Credentials)

    def test_get_credentials_without_file_returns(self):
        environ['GOOGLE_APPLICATION_CREDENTIALS'] = _TEST_CREDENTIALS_FILE_PATH
        gcp_auth = GcpAuth()
        self.assertIsInstance(gcp_auth.credentials, credentials.Credentials)


def suite():
    test_suite = TestSuite()
    test_suite.addTest(
        TestGetCredentials('test_get_credentials_without_file_returns'))
    test_suite.addTest(
        TestGetCredentials('test_get_credentials_from_file_returns'))
    return test_suite


if __name__ == '__main__':
    if is_running_under_teamcity():
        runner = TeamcityTestRunner
    else:
        runner = TextTestRunner(verbosity=2).run(suite())
    main(testRunner=runner)
