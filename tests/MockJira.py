from jira import Issue
from unittest.mock import MagicMock


class MockJira:
    def __init__(self, server=None, basic_auth=None):
        self.auth = basic_auth
        self.server = server

    def search_issues(self, filter_id):
        assert isinstance(filter_id, str)
        return [self.issue(key) for key in ['GCP-123', 'GCP-321']]

    @staticmethod
    def issue(key):
        assert isinstance(key, str)
        project_id = 'test-12345678-' + key + 'dev'
        return MagicMock(Issue, raw={
            'fields': {'customfield_1234': project_id},
            'key': key
        })
