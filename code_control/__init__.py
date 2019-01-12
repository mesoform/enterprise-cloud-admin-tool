#!/usr/bin/env python
from __future__ import print_function


import json
import argparse
import requests
import os
# github package is PyGithub
# noinspection PyPackageRequirements
from github import GithubException, BadCredentialsException
from exceptions import ValueError
from builder import get_team, get_repo, get_org, arg_parser, \
    DEFAULT_PROJECT_ID, DEFAULT_TOKEN_FILE

MODULE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_GITHUB_API_URL = "https://api.github.com"
ADMIN_TEAM = 'gcp-admin-team'
STANDARD_TEAM_ATTRIBUTES = {
    "name": DEFAULT_PROJECT_ID,
    "permission": "push",
    "description": 'Standard team for ' + DEFAULT_PROJECT_ID + ' project',
    "privacy": "closed"
}
PRIV_TEAM_ATTRIBUTES = {
    "name": DEFAULT_PROJECT_ID + '-priv',
    "permission": "push",
    "description": 'Privileged team for ' + DEFAULT_PROJECT_ID + ' project',
    "privacy": "secret"
}
PROJECT_DATA_DIR = \
    MODULE_ROOT_DIR + 'resources/project_data/' + DEFAULT_PROJECT_ID
PROTECTED_BRANCH = {
    "enforce_admins": True,
    "dismiss_stale_reviews": True,
    "require_code_owner_reviews": False,
    "required_approving_review_count": 1
}
HIGHLY_PROTECTED_BRANCH = {
    "enforce_admins": True,
    "dismiss_stale_reviews": True,
    "require_code_owner_reviews": True,
    "required_approving_review_count": 2
}
LOCAL_FILES = {
    'readme_file':
        MODULE_ROOT_DIR + 'resources/templates/README.md',
    'apis_file':
        MODULE_ROOT_DIR + 'resources/templates/gcp_enabled_apis.json',
    'project_settings_file':
        MODULE_ROOT_DIR + 'resources/templates/gcp_project_settings.json',
    'role_bindings_file':
        MODULE_ROOT_DIR + 'resources/templates/gcp_role_bindings.json',
    'service_accounts_file':
        MODULE_ROOT_DIR + 'resources/templates/gcp_service_accounts.json'
}
REMOTE_FILES = {
    'readme_file': 'README.md',
    'apis_file': 'sot/gcp_enabled_apis.json',
    'project_settings_file': 'sot/gcp_project_settings.json',
    'role_bindings_file': 'sot/gcp_role_bindings.json',
    'service_accounts_file': 'sot/gcp_service_accounts.json'
}


def add_args():
    """
    parses arguments passed on command line when running program
    :return: Object
    """
    parser = argparse.ArgumentParser(
        description='Maintain Github repositories and teams',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.set_defaults(change_files=LOCAL_FILES,
                        branch_permissions=PROTECTED_BRANCH)
    parser.add_argument('-b', '--branch-protection',
                        choices=('standard', 'high'),
                        help='\nThe level to which the branch will be '
                             'protected\n'
                             'standard: adds review requirements, stale reviews'
                             ' and admin enforcement\n'
                             'high: also code owner reviews and review count',
                        default='standard',
                        action=BranchProtectArgAction)
    parser.add_argument('--bypass-branch-protection',
                        help='Bypasses branch protection when updating files'
                             ' which already exist in the repository',
                        default=False,
                        action='store_true')
    parser.add_argument('-O', '--output-data',
                        help='Output repo data to files in ' + PROJECT_DATA_DIR,
                        action='store_true')
    parser.add_argument('--templates-repo',
                        help='Repository where default templates are stored',
                        action=TemplatesArgAction)

    return parser


class TemplatesArgAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(TemplatesArgAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        setattr(namespace, 'change_files', REMOTE_FILES)


class BranchProtectArgAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(BranchProtectArgAction, self).__init__(option_strings, dest,
                                                     **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        branch_permissions = None
        if values == 'standard':
            branch_permissions = PROTECTED_BRANCH
        if values == 'high':
            branch_permissions = HIGHLY_PROTECTED_BRANCH
        setattr(namespace, 'branch_permissions', branch_permissions)


def __get_default_config_file(repo, remote_file):
    return repo.get_contents(remote_file, ref="master")


def create_repo(org, name=DEFAULT_PROJECT_ID):
    """
    creates the GitHub repository
    :param org: obj: organisation where the repo will sit
    :param name: string: name of the repo
    :return: obj: github.Repository.Repository
    """
    return org.create_repo(name=name,
                           description="GCP Project config for " + name)


class GithubFileExists(Exception):
    pass


def update_repo_file(repo, file_to_change, new_content, commit_msg,
                     force=False, bypass_protection=False):
    """
    Updates the files on the newly project repository
    :param bypass_protection: bool:  whether to bypass protection on branch
    :param force: bool: whether or not to force an update to an existing file
    :param repo: obj: repository we're modifying
    :param file_to_change: str: of the path relative to the file in the repo
    :param new_content: str: to write to the file in Github
    :param commit_msg: str: message to go with the git commit
    """
    try:
        cur_file = repo.get_contents(file_to_change, ref="master")
    except GithubException as e:
        cur_file = None
        print(e.data)
        print(file_to_change + " doesn't exist. Creating...")

    if cur_file and force is True:
        print("Updating file " + file_to_change)
        try:
            repo.update_file(cur_file.path,
                             commit_msg + file_to_change,
                             new_content,
                             cur_file.sha,
                             branch="master")
        except GithubException as e:
            if e.status == 409 and bypass_protection:
                set_master_branch_permissions(repo, {})
                update_repo_file(
                    repo, file_to_change, new_content, commit_msg, force,
                    bypass_protection
                )
            else:
                print(e.data)
                print("Try --bypass-branch-protection")
    elif cur_file and force is not True:
        raise GithubFileExists("File " + file_to_change
                               + " already exists. Use --force to reconfigure")
    else:
        repo.create_file(file_to_change,
                         commit_msg,
                         new_content,
                         branch="master")


def create_team(org,
                team_name=STANDARD_TEAM_ATTRIBUTES["name"],
                permission=STANDARD_TEAM_ATTRIBUTES["permission"],
                privacy=STANDARD_TEAM_ATTRIBUTES["privacy"]):
    """
    creates the organisation team
    :param org: obj: organisation where the team will be part of
    :param team_name: string: name of the team
    :param privacy: string: whether team should be secret or public
    :param permission: string: what rights the team should have
    :return: obj: github.Team.Team
    """
    existing_team = get_team(org, team_name)
    if existing_team:
        existing_team.edit(name=team_name,
                           permission=permission, privacy=privacy)
        return existing_team

    return org.create_team(name=team_name,
                           permission=permission, privacy=privacy)


def configure_remote_object(url, token, **kwargs):
    """
    uses request module to pass headers needed for beta API feature of setting
    parent_id in API and attributes missing from PyGithub library
    :param token: authentication token header
    :param url: URL to access object
    :param kwargs: key value pairs of object attributes to set
    """
    data = {}
    data.update(**kwargs)
    headers = {
        'Accept': 'application/vnd.github.hellcat-preview+json',
        'Authorization': 'token ' + token
    }

    response = requests.patch(url=url, headers=headers, data=json.dumps(data))
    if response.status_code != 200:
        print("ERROR: FAILED TO UPDATE OBJECT")
        print(response.headers)
        print(response.text)

    return response


def configure_project_data(config_file, **kwargs):
    """
    takes a JSON template file with config defaults, sets any new values based
    on kwargs returns a JSON string ready to be used in git file update
    :param config_file: str: path to template file containing defaults
    :param kwargs: list: of key/value pairs to set in dict
    :return: string
    """
    with open(config_file, 'r') as settings_file:
        data_dict = json.loads(settings_file.read())
    data_dict.update(**kwargs)
    return json.dumps(data_dict, indent=2)


def write_project_data(repo, teams, data_dir=PROJECT_DATA_DIR):
    if not os.path.isdir(data_dir):
        os.mkdir(data_dir, 0700)

    repo_file = data_dir + '/repo.json'
    with open(repo_file, 'w') as rf:
        rf.write(json.dumps(repo.raw_data, indent=2))
    for team in teams:
        team_file = data_dir + "/team_" + team.slug + '.json'
        with open(team_file, 'w') as tf:
            tf.write(json.dumps(team.raw_data, indent=2))


def set_repo_visibility(repo, visibility):
    """
    Sets whether the repository can be seen publicly or not
    :param repo: obj: Github repository to configure
    :param visibility: str: public or private
    """
    if visibility == 'private':
        repo.edit(private=True)
    elif visibility == 'public':
        repo.edit(private=False)
    else:
        raise ValueError


def set_repo_team_perms(org, repo, team_id, permission):
    """
    Sets the permissions of a team on a repository
    :param org: obj: the organisation where the repository and team are
    :param repo: obj: the repository we're giving access to
    :param team_id: int: the ID of the team that is gaining access
    :param permission: str: one of read (pull), write (push) or admin (admin)
    """
    team = org.get_team(team_id)
    if permission == 'read':
        team.set_repo_permission(repo, 'pull')
    elif permission == 'write':
        team.set_repo_permission(repo, 'push')
    else:
        team.set_repo_permission(repo, permission)


def set_master_branch_permissions(repo, branch_permissions):
    """
    set relevant protections on the master branch as described in
    github.BranchProtection.BranchProtection
    :param repo: obj: repository we're setting branch permissions on
    :param branch_permissions: dict: keys and values described in
                    github.BranchProtection.BranchProtection
    """
    master = repo.get_branch('master')
    if not branch_permissions:
        master.remove_protection()
    master.edit_protection(**branch_permissions)


def __file_content(file_with_content):
    with open(file_with_content) as content:
        return content.read()


def main():
    settings = arg_parser().parse_args()
    # grab the last field from delimited project name
    environment = settings.project_id.upper().split('-').pop()
    try:
        org = get_org(settings, settings.config_org)
    except BadCredentialsException as e:
        print(e.data)
        print("check token and pass using the --token (-t) argument or setting"
              "the token in " + DEFAULT_TOKEN_FILE)
        raise BadCredentialsException(e.status, e.data)
    existing_repo = get_repo(org, settings.project_id)

    if existing_repo and not settings.force:
        print("Repository " + settings.project_id
              + " already exists. Use --force to reconfigure")
        exit(1)
    elif existing_repo and settings.force:
        repo = existing_repo
        commit_msg = "Update "
    else:
        repo = create_repo(org, name=settings.project_id)
        commit_msg = "Initial commit"

    # Configure project
    for config_file in settings.change_files.keys():
        if config_file == 'project_settings_file':
            config = configure_project_data(
                settings.change_files[config_file],
                project_id=settings.project_id,
                project_name=settings.project_id,
                folder_id=environment + "-Environment")
        else:
            config = __file_content(settings.change_files[config_file])
        # Todo: capture update_repo_content exception and exclude if --force is
        #  set
        try:
            # noinspection PyUnboundLocalVariable
            update_repo_file(repo, REMOTE_FILES[config_file], config,
                             commit_msg, settings.force,
                             settings.bypass_branch_protection)
        except GithubException as e:
            print(e.data)

    # Create teams
    std_team = create_team(org)
    priv_team = create_team(org, PRIV_TEAM_ATTRIBUTES["name"],
                            PRIV_TEAM_ATTRIBUTES["permission"])
    admin_team = get_team(org, ADMIN_TEAM)
    configure_remote_object(std_team.url, settings.token,
                            description=STANDARD_TEAM_ATTRIBUTES["description"])
    configure_remote_object(priv_team.url, settings.token,
                            parent_team_id=std_team.id,
                            description=PRIV_TEAM_ATTRIBUTES["description"])

    # Set repository permission
    if admin_team:
        set_repo_team_perms(org, repo, admin_team.id, 'admin')
    set_repo_team_perms(org, repo, std_team.id, 'read')
    set_repo_team_perms(org, repo, priv_team.id, 'write')
    try:
        set_repo_visibility(repo, 'private')
    except GithubException as e:
        print(e.data)

    set_master_branch_permissions(repo, settings.branch_permissions)
    if settings.output_data:
        write_project_data(repo, [std_team, priv_team])


if __name__ == '__main__':
    main()
