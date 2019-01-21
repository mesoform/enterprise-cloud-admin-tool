from __future__ import print_function

import argparse
import os
import json
# noinspection PyPackageRequirements
from github import Github, GithubException
from exceptions import ValueError
import re

MODULE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GITHUB_API_URL = "https://api.github.com"
DEFAULT_PROJECT_NAME = "my-gcp-project"
DEFAULT_PROJECT_ID = "my-gcp-project"
DEFAULT_CODE_ORG = 'my-code-org'
DEFAULT_CONFIG_ORG = 'my-config-org'
PROJECT_DATA_DIR = MODULE_ROOT_DIR + 'resources/project_data/' + \
                   DEFAULT_PROJECT_ID
DEFAULT_TOKEN_FILE = MODULE_ROOT_DIR + '/resources/token.json'
DEFAULT_GIT_REF = 'master'
if os.path.exists(DEFAULT_TOKEN_FILE):
    DEFAULT_TOKEN = json.load(open(DEFAULT_TOKEN_FILE))['token']
else:
    DEFAULT_TOKEN = ""
SUPPORTED_CLOUDS = ['aws', 'gcp', 'triton']
SUPPORTED_VCS_PLATFORMS = ['github']
SUPPORTED_ORCHESTRATORS = ['terraform']
VALID_PROJECT_ID_FORMAT = "^[a-z]{4}-[a-z0-9]{4,31}-(?:dev|prod|test)$"


class ProjectIdFormatError(Exception):
    pass


class RepositoryNotFoundError(Exception):
    pass


def arg_parser():
    """
    parses arguments passed on command line when running program
    :return: list of arguments
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter)
    parser.set_defaults(force=False)
    parser.add_argument('-a', '--api_url',
                        help='URL to GitHub API',
                        default=DEFAULT_GITHUB_API_URL)
    parser.add_argument('--code-version',
                        help='version (branch or tag) of the deployment code '
                             'to use',
                        default='master')
    parser.add_argument('--config-version',
                        help='version (branch or tag) of the cloud '
                             'configuration to use',
                        default='master')
    parser.add_argument('-f', '--force',
                        help='Force actions on preexisting repo',
                        default=False,
                        action='store_true')
    parser.add_argument('--output-data',
                        help='Output repo data to files in ' + PROJECT_DATA_DIR,
                        action='store_true')
    parser.add_argument('-o', '--code-org',
                        help="ID of the organisation where the Terraform code"
                             "repository is",
                        default=DEFAULT_CODE_ORG)
    parser.add_argument('-O', '--config-org',
                        help="ID of the organisation where the configuration"
                             "repository is",
                        default=DEFAULT_CONFIG_ORG)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-p', '--project-id',
                       help="ID of project we're creating a repository for",
                       default=DEFAULT_PROJECT_NAME)
    group.add_argument('-q', '--queued-projects',
                       help="fetch a list of projects from requests queue",
                       action=QueuedProjectsArgAction)
    parser.add_argument('-t', '--token',
                        help='Token for authentication')
    parser.add_argument('-c', '--config-version',
                        help="git branch for the configuration",
                        default=DEFAULT_GIT_REF)
    parser.add_argument('-T', '--code-version',
                        help="git branch for the code",
                        default=DEFAULT_GIT_REF)
    
    return parser


class QueuedProjectsArgAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(QueuedProjectsArgAction, self).__init__(option_strings, dest,
                                                      nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        # ToDo: add function call to get projects list from JIRA
        setattr(namespace, 'projects_list', [])


def get_org(settings, org):
    github = Github(
        base_url=settings.api_url, login_or_token=settings.token)
    return github.get_organization(org)


def get_repo(org, name=DEFAULT_PROJECT_ID):
    repo = None
    try:
        repo = org.get_repo(name)
    except GithubException as e:
        print(e.data)
    return repo


def get_team(org, team_name):
    """
    returns team from org by searching the name
    :param org: obj: of the organisation to search
    :param team_name: string: name of the team to return
    :return: obj: github.Team.Team
    """
    for team in org.get_teams():
        if team.slug == team_name:
            return team
    return None


def get_files(org, repo_name, directory, version):
    """
    Get a list of the files from given repository
    :param org: object: of :class:`github.Organization.Organization`
    :param repo_name: string: of name of the organisational repository where
     files are located
    :param directory: string: of directory in reposo
    :param version: string : branch or tag of repo
    :return: list :class:`github.ContentFile.ContentFile`
    """
    repo = get_repo(org, repo_name)
    return repo.get_dir_contents(directory, version)


def valid_project_id_format(project_id):
    if not re.match(VALID_PROJECT_ID_FORMAT, project_id):
        raise ProjectIdFormatError(project_id + ' does not match the ' +
                                   VALID_PROJECT_ID_FORMAT + 'format')
    return True
