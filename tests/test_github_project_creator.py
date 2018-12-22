#!/usr/bin/env python

from unittest import TestLoader, TestCase, TextTestRunner
import json
import os
from github import Organization, Team, Repository
from exceptions import ValueError
from github_project_creator import get_org, create_repo, create_team, \
    get_repo, configure_remote_object, update_repo_file, \
    configure_project_data, set_repo_team_perms, set_master_branch_permissions,\
    write_project_data, set_repo_visibility, DEFAULT_GITHUB_API_URL

TOKEN = json.load(open('resources/token.json'))['token']
GCP_PROJECT_TEMPLATE = 'resources/templates/gcp_project_settings.json'
GCP_PROJECT_DATA = json.loads(
    open('resources/project_data/gcp_project_settings.json', 'r').read())
ORG_NAME = 'mesoform'
PROJECT_NAME = 'test-project'
TEAM_NAME = 'test-team'
CHILD_TEAM_NAME = TEAM_NAME + '-child'
STANDARD_TEAM_ATTRIBUTES = {
    "name": PROJECT_NAME,
    "permission": "push",
    "description": 'Standard team for ' + PROJECT_NAME + ' project',
    "privacy": "closed"
}


def arguments():
    arg_dict = {"org": ORG_NAME,
                "project_name": PROJECT_NAME,
                "templates_repo": None,
                "token": TOKEN,
                "api_url": DEFAULT_GITHUB_API_URL
                }
    args = type('', (), {})()
    args.__dict__.update(arg_dict)
    return args


class TestOrg(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = arguments()

    def test_org_setup(self):
        self.assertIsInstance(
            get_org(self.settings), Organization.Organization)


class TestRepo(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = arguments()
        cls.org = get_org(cls.settings)
        existing_repo = get_repo(cls.org, PROJECT_NAME)
        if existing_repo:
            cls.repo = existing_repo
        else:
            cls.repo = create_repo(cls.org, PROJECT_NAME)

    def test_create_and_get_repo(self):
        """
        Tests if the repo created in the setUpClass method correct
        """
        self.assertIsInstance(get_repo(self.org, PROJECT_NAME),
                              Repository.Repository)

    def test_content_update(self):
        """
        Tests if we can update any content in the repo we created
        """
        new_readme_file = 'resources/templates/README.md'
        with open(new_readme_file, 'r') as readme:
            expected_readme_contents = readme.read()
            update_repo_file(self.repo, 'README.md',
                             expected_readme_contents,
                             'Test commit')
        actual_readme_contents = self.repo.get_contents(
            'README.md', ref="master").decoded_content
        self.assertEqual(
            actual_readme_contents,
            expected_readme_contents
        )

    def test_configure_project_data(self):
        """
        Tests that we can modify data correctly from our templates
        """
        new_data = configure_project_data(GCP_PROJECT_TEMPLATE,
                                          project_id=PROJECT_NAME,
                                          project_name=PROJECT_NAME,
                                          billing_id="123-456-789",
                                          folder_id="DEV")
        self.assertDictEqual(json.loads(new_data), GCP_PROJECT_DATA)

    def test_setting_branch_permissions(self):
        """
        Tests whether the function to set branch permissions works
        """
        set_master_branch_permissions(self.repo, {"enforce_admins": True})
        branch_protection = self.repo.get_branch('master').get_protection()
        self.assertTrue(branch_protection.enforce_admins)

    def test_set_repo_visibility(self):
        with self.assertRaises(ValueError):
            set_repo_visibility(self.repo, 'magic_invisible_cloak')
        set_repo_visibility(self.repo, 'public')
        self.assertFalse(self.repo.private)

    @classmethod
    def tearDownClass(cls):
        cls.repo.delete()


class TestTeam(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = arguments()
        cls.org = get_org(cls.settings)
        cls.repo = create_repo(cls.org, PROJECT_NAME)
        cls.team = create_team(cls.org, TEAM_NAME)
        cls.team_child = create_team(cls.org, CHILD_TEAM_NAME)
        cls.bad_team_child = create_team(cls.org, 'bad-' + CHILD_TEAM_NAME,
                                         privacy="secret")
        cls.test_data_dir = '/tmp/' + PROJECT_NAME
        cls.team_out_file = cls.test_data_dir + "/team_" + TEAM_NAME + '.json'
        cls.repo_out_file = cls.test_data_dir + '/repo.json'

    def test_create_team(self):
        """
        Tests if we can update any content in the repo we created
        """
        self.assertIsInstance(self.org.get_team(self.team.id), Team.Team)
        # Can't test as parent_team_id is beta
        # self.assertEqual(self.org.get_team(self.team_child.id).parent_team_id,
        #                  self.team.id)

    def test_configure_team(self):
        """
        Configuring team requires some beta features and is handled in a
        different function as a result. Tests that we've configured the team
        as expected
        """
        configure_remote_object(self.team_child.url, TOKEN,
                                parent_team_id=self.team.id,
                                description="test description")
        self.assertEqual(self.org.get_team(self.team_child.id).description,
                         "test description")
        config_response = configure_remote_object(
            self.bad_team_child.url, TOKEN,
            parent_team_id=self.team.id,
            description="test description")
        self.assertFalse(config_response.ok)

    def test_setting_repo_team_permissions(self):
        """
        Test that we've been able to grant the correct access to the team's
        repository
        """
        set_repo_team_perms(self.org, self.repo, self.team_child.id, 'read')
        self.assertTrue(self.team_child.has_in_repos(self.repo))

    def test_writing_project_objects(self):
        write_project_data(self.repo, [self.team],
                           self.test_data_dir)
        self.assertDictEqual(
            json.loads(open(self.repo_out_file).read()),
            self.repo.raw_data
        )

    @classmethod
    def tearDownClass(cls):
        cls.team_child.delete()
        cls.team.delete()
        cls.bad_team_child.delete()
        cls.repo.delete()
        os.remove(cls.team_out_file)
        os.remove(cls.repo_out_file)
        os.rmdir(cls.test_data_dir)


if __name__ == '__main__':
    suite = TestLoader()
    suite.loadTestsFromTestCase(TestOrg)
    suite.loadTestsFromTestCase(TestRepo)
    suite.loadTestsFromTestCase(TestTeam)
    TextTestRunner(verbosity=2).run(suite)
