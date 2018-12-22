#!/usr/bin/env python

import json
import python_terraform
import terraform_validate
import github
import argparse
import os
import builder


MODULE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_BRANCH = 'master'
DEFAULT_CODE_BRANCH = 'master'
DEFAULT_TOKEN_FILE = MODULE_ROOT_DIR + '/resources/token.json'
with open(DEFAULT_TOKEN_FILE) as f:
    DEFAULT_TOKEN = json.load(f)['token']
DEFAULT_CODE_ORG = 'mesoform'
DEFAULT_CONFIG_ORG = 'mesoform'
DEFAULT_GITHUB_API_URL = "https://api.github.com"
DEFAULT_CONFIG_REPO = "terraform-deployment-module"
DEFAULT_CODE_REPO = "terraform-deployment-module"


def add_args():
    """
    parses arguments passed on command line when running program
    :return: list of arguments
    """
    parser = builder.arg_parser()
    parser.description = 'General module for processing and deploying ' \
                         'infrastructure'
    parser.add_argument('-c', '--config-version',
                        help="git branch for the configuration",
                        default=DEFAULT_CONFIG_BRANCH)
    parser.add_argument('-o', '--code-organisation',
                        help="ID of the organisation where the Terraform code"
                             "repository is",
                        default=DEFAULT_CODE_ORG)
    parser.add_argument('-O', '--config-organisation',
                        help="ID of the organisation where the configuration"
                             "repository is",
                        default=DEFAULT_CONFIG_ORG)
    parser.add_argument('-T', '--code-version',
                        help="git branch for the code",
                        default=DEFAULT_CODE_BRANCH)
    return parser.parse_args()


def get_files(version, repo=DEFAULT_CODE_REPO):
    return repo.get_content_files()


def main():
    settings = add_args()
    # needs to differentiate between orgs and repo for code and config 
    config_org = builder.get_org(settings)
    config_repo = builder.get_repo(config_org, settings.project_name)
    config = get_files(settings.config_version, config_repo)
    # pull args.tf_code_version (default = master)
    # pull files from args.branch
    code_org = builder.get_org(settings)
    code_repo = builder.get_repo(code_org, settings.project_name)
    code = get_files(settings.code_version, code_repo)
    # pass through code checker 
    # test deploy 
    # compare test project state file against actual state file 
    # plan
    # deploy 
    # validate 
    pass


if __name__ == '__main__':
    main()
