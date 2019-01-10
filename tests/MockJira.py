from jira import Issue
from unittest.mock import MagicMock
  
class MockJira:
  def __init__(self, server=None, basic_auth=None):
    self.auth = basic_auth
    self.server = server
    
  def search_issues(self, filter_id):
    assert isinstance(filter_id, str)
    return [issue(id) for id in ['GCP-123', 'GCP-321']]
             
  def issue(self, id):
    assert isinstance(id, str)
    project_id = 'test-12345678-' + id + 'dev'
    return MagicMock(Issue, raw={
      'fields': {'customfield_1234': project_id},
      'key': id
      })
     
