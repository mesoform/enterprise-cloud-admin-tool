import re
import argparse
import os
import json

from github import Github
from httplib2 import Http

from settings import SETTINGS


class ProjectIdFormatError(Exception):
    pass


class RepositoryNotFoundError(Exception):
    pass


def root_parser():
    """
    parses arguments passed on command line when running program
    :return: list of arguments
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.set_defaults(force=False)
    parser.add_argument(
        "--api-url",
        "-a",
        help="URL to GitHub API",
        default=SETTINGS.DEFAULT_GITHUB_API_URL,
    )
    parser.add_argument(
        "--code-org",
        "-o",
        help="ID of the organisation where the Terraform code" "repository is",
        default=SETTINGS.DEFAULT_CODE_ORG,
    )
    parser.add_argument(
        "--config-org",
        "-O",
        help="ID of the organisation where the configuration" "repository is",
        default=SETTINGS.DEFAULT_CONFIG_ORG,
    )
    parser.add_argument(
        "--vcs-token",
        "-t",
        help="Authentication for VCS platform"
    )
    parser.add_argument(
        "--config-version",
        "-c",
        help="git branch for the configuration",
        default=SETTINGS.DEFAULT_GIT_REF,
    )
    parser.add_argument(
        "--code-version",
        "-T",
        help="git branch for the code",
        default=SETTINGS.DEFAULT_GIT_REF,
    )
    parser.add_argument(
        "--key-file",
        help="path to the file containing the private "
        "key used for authentication on CSP",
        type=argparse.FileType("r"),
    )
    parser.add_argument(
        "--monitoring-namespace",
        help="CSP specific location where monitoring data is aggregated. For"
        "example, a GCP project",
    )
    parser.add_argument(
        "--log-file",
        help="path to log file, if different from default",
        default=SETTINGS.DEFAULT_LOG_FILE,
    )
    parser.add_argument(
        "--metrics-file",
        help="path to file containing monitoring metrics, if different from default",
        default=SETTINGS.DEFAULT_METRICS_FILE,
    )
    parser.add_argument(
        "--debug",
        help="output debug information to help troubleshoot issues",
        default=False,
    )
    parser.add_argument(
        "--disable-local-reporter",
        help="disable logging and monitoring to local files",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--json-logging",
        help="Enable logging in json logging format",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--slack-token",
        "-st",
        help="Slack bot user OAuth access token"
    )
    parser.add_argument(
        "--slack-channel",
        "-sc",
        help="Name of channel, where notifications will go",
    )
    parser.add_argument(
        "--vcs-platform",
        choices=["all"] + SETTINGS.SUPPORTED_VCS_PLATFORMS,
        default="github"
    )
    return parser


class GcpAuth:
    def __init__(self, key_file=None):
        self.key_file = key_file
        if self.key_file:
            self.service_account_info = self._get_service_account_info(key_file)
        self.credentials = self.get_gcp_credentials()

    def get_gcp_credentials(self):
        """
        construct credentials object to authenticate against APIs with
        :return: object: of type google.auth.credentials.Credentials
        """
        if self.key_file:
            from google.oauth2 import service_account

            return service_account.Credentials.from_service_account_info(
                self.service_account_info
            )
        else:
            import google.auth

            credentials, project_id = google.auth.default()
            return credentials

    def _get_http_auth(self):
        """
        Add credentials to an HTTP request object
        :return: HTTP request object with added credential information
        """
        credentials = self.get_gcp_credentials()
        return credentials.authorize(Http())

    @staticmethod
    def _get_service_account_info(creds_file):
        with open(creds_file.name, "r") as f:
            ext = os.path.splitext(f.name)[-1].lower()
            if ext == ".json":
                return json.loads(f.read())

    # def _get_project_id():
    #     """
    #     query Google Metadata server
    #     :return: string of project id
    #     """
    #     url = GCP_METADATA_URL + '/project/project-id'
    #     try:
    #         project_id = requests.get(url)
    #     except (requests.ConnectionError, requests.ConnectTimeout):
    #         return _DEFAULT_GCP_PROJECT
    #
    #     return project_id
    #
    # def _get_storage_client(storage_class=storage.Client):
    #     """
    #     set up our local storage client
    #     :param storage_class: what Python class to use to set up our client
    #     :return: Object of our client
    #     """
    #     return storage_class(project=_get_project_id(),
    #                          credentials=get_gcs_credentials())


def get_org(parsed_args, org):
    github = Github(
        base_url=parsed_args.api_url, login_or_token=parsed_args.vcs_token
    )
    return github.get_organization(org)


def get_repo(org, name=SETTINGS.DEFAULT_PROJECT_ID):
    return org.get_repo(name)


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


def get_hash_of_latest_commit(org, repo_name, branch):
    """
    Get sha256 hash of latest commit in some branch of the repo.
    :param org: object: of :class:`github.Organization.Organization`
    :param repo_name: string: of name of the organisational repository where
     files are located
    :param branch: string : name of the git branch
    :return: sha256 hash string
    """
    repo = get_repo(org, repo_name)
    branch = repo.get_branch(branch)
    return branch.commit.sha


def valid_project_id_format(project_id):
    if not re.match(SETTINGS.VALID_PROJECT_ID_FORMAT, project_id):
        raise ProjectIdFormatError(
            project_id
            + " does not match the "
            + SETTINGS.VALID_PROJECT_ID_FORMAT
            + "format"
        )
    return True
