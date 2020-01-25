import argparse
import json
import os
import requests

# github package is PyGithub
# noinspection PyPackageRequirements
from github import GithubException, BadCredentialsException
from common import get_team, get_repo, get_org

from settings import SETTINGS


class TemplatesArgAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(TemplatesArgAction, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        setattr(namespace, "change_files", SETTINGS.REMOTE_FILES)


class BranchProtectArgAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super(BranchProtectArgAction, self).__init__(
            option_strings, dest, **kwargs
        )

    def __call__(self, parser, namespace, values, option_string=None):
        branch_permissions = None
        if values == "standard":
            branch_permissions = SETTINGS.PROTECTED_BRANCH
        if values == "high":
            branch_permissions = SETTINGS.HIGHLY_PROTECTED_BRANCH
        setattr(namespace, "branch_permissions", branch_permissions)


def __get_default_config_file(repo, remote_file):
    return repo.get_contents(remote_file, ref="master")


def create_repo(org, name=SETTINGS.DEFAULT_PROJECT_ID):
    """
    creates the GitHub repository
    :param org: obj: organisation where the repo will sit
    :param name: string: name of the repo
    :return: obj: github.Repository.Repository
    """
    return org.create_repo(
        name=name, description="GCP Project config for " + name
    )


class GithubFileExists(Exception):
    pass


def update_repo_file(
    repo,
    file_to_change,
    new_content,
    commit_msg,
    force=False,
    bypass_protection=False,
):
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
            repo.update_file(
                cur_file.path,
                commit_msg + file_to_change,
                new_content,
                cur_file.sha,
                branch="master",
            )
        except GithubException as e:
            if e.status == 409 and bypass_protection:
                set_master_branch_permissions(repo, {})
                update_repo_file(
                    repo,
                    file_to_change,
                    new_content,
                    commit_msg,
                    force,
                    bypass_protection,
                )
            else:
                print(e.data)
                print("Try --bypass-branch-protection")
    elif cur_file and force is not True:
        raise GithubFileExists(
            "File "
            + file_to_change
            + " already exists. Use --force to reconfigure"
        )
    else:
        repo.create_file(
            file_to_change, commit_msg, new_content, branch="master"
        )


def create_team(
    org,
    team_name=SETTINGS.STANDARD_TEAM_ATTRIBUTES["name"],
    permission=SETTINGS.STANDARD_TEAM_ATTRIBUTES["permission"],
    privacy=SETTINGS.STANDARD_TEAM_ATTRIBUTES["privacy"],
):
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
        existing_team.edit(
            name=team_name, permission=permission, privacy=privacy
        )
        return existing_team

    return org.create_team(
        name=team_name, permission=permission, privacy=privacy
    )


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
        "Accept": "application/vnd.github.hellcat-preview+json",
        "Authorization": "token " + token,
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
    with open(config_file, "r") as settings_file:
        data_dict = json.loads(settings_file.read())

    data_dict.update(**kwargs)
    return json.dumps(data_dict, indent=2)


def write_project_data(repo, teams, data_dir=SETTINGS.PROJECT_DATA_DIR):
    if not os.path.isdir(data_dir):
        os.mkdir(data_dir, 0o0700)

    repo_file = data_dir + "/repo.json"
    with open(repo_file, "w") as rf:
        rf.write(json.dumps(repo.raw_data, indent=2))
    for team in teams:
        team_file = data_dir + "/team_" + team.slug + ".json"
        with open(team_file, "w") as tf:
            tf.write(json.dumps(team.raw_data, indent=2))


def set_repo_visibility(repo, visibility):
    """
    Sets whether the repository can be seen publicly or not
    :param repo: obj: Github repository to configure
    :param visibility: str: public or private
    """
    if visibility == "private":
        repo.edit(private=True)
    elif visibility == "public":
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
    if permission == "read":
        team.set_repo_permission(repo, "pull")
    elif permission == "write":
        team.set_repo_permission(repo, "push")
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
    master = repo.get_branch("master")
    if not branch_permissions:
        master.remove_protection()
    master.edit_protection(**branch_permissions)


def __file_content(file_with_content):
    with open(file_with_content) as content:
        return content.read()


def setup(parsed_args):
    # grab the last field from delimited project name
    environment = parsed_args.project_id.upper().split("-").pop()
    try:
        org = get_org(parsed_args, parsed_args.config_org)
    except BadCredentialsException as e:
        print(e.data)
        print(
            "check token and pass using the --vcs-token (-t) argument or setting"
            "the token in " + SETTINGS.DEFAULT_TOKEN_FILE
        )
        raise BadCredentialsException(e.status, e.data)

    try:
        existing_repo = get_repo(org, parsed_args.config_repo)
    except GithubException as e:
        if e.status == 404:
            existing_repo = None
        else:
            raise

    if existing_repo and not parsed_args.force:
        print(
            "Repository "
            + parsed_args.config_repo
            + " already exists. Use --force to reconfigure"
        )
        exit(1)
    elif existing_repo and parsed_args.force:
        repo = existing_repo
        commit_msg = "Update "
    else:
        repo = create_repo(org, name=parsed_args.config_repo)
        commit_msg = "Initial commit"

    # Configure project
    for config_file in parsed_args.change_files.keys():
        if config_file == "project_settings_file":
            config = configure_project_data(
                parsed_args.change_files[config_file],
                project_id=parsed_args.project_id,
                project_name=parsed_args.project_id,
            )
        else:
            config = __file_content(parsed_args.change_files[config_file])
        # Todo: capture update_repo_content exception and exclude if --force is
        #  set
        try:
            # noinspection PyUnboundLocalVariable
            update_repo_file(
                repo,
                SETTINGS.REMOTE_FILES[config_file],
                config,
                commit_msg,
                parsed_args.force,
                parsed_args.bypass_branch_protection,
            )
        except GithubException as e:
            print(e.data)

    # Create teams
    std_team = create_team(org)
    priv_team = create_team(
        org,
        SETTINGS.PRIV_TEAM_ATTRIBUTES["name"],
        SETTINGS.PRIV_TEAM_ATTRIBUTES["permission"],
    )
    admin_team = get_team(org, SETTINGS.ADMIN_TEAM)
    configure_remote_object(
        std_team.url,
        parsed_args.vcs_token,
        description=SETTINGS.STANDARD_TEAM_ATTRIBUTES["description"],
    )
    configure_remote_object(
        priv_team.url,
        parsed_args.vcs_token,
        parent_team_id=std_team.id,
        description=SETTINGS.PRIV_TEAM_ATTRIBUTES["description"],
    )

    # Set repository permission
    if admin_team:
        set_repo_team_perms(org, repo, admin_team.id, "admin")
    set_repo_team_perms(org, repo, std_team.id, "read")
    set_repo_team_perms(org, repo, priv_team.id, "write")
    try:
        set_repo_visibility(repo, "private")
    except GithubException as e:
        print(e.data)

    set_master_branch_permissions(repo, parsed_args.branch_permissions)
    if parsed_args.output_data:
        write_project_data(repo, [std_team, priv_team])

    return True
