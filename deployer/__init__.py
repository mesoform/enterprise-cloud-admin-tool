#!/usr/bin/env python
from __future__ import print_function, absolute_import

import json
import python_terraform
import os
import builder


MODULE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_BRANCH = 'master'
DEFAULT_CODE_BRANCH = 'master'


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
    parser.add_argument('-T', '--code-version',
                        help="git branch for the code",
                        default=DEFAULT_CODE_BRANCH)
    return parser.parse_args()


def main():
    settings = add_args()
    # needs to differentiate between orgs and repo for code and config
    config_org = builder.get_org(settings)
    config_repo = builder.get_repo(config_org, settings.project_name)
    config_files = builder.get_files(settings.config_version, config_repo)
    # pull args.tf_code_version (default = master)
    # pull files from args.branch
    code_org = builder.get_org(settings)
    code_repo = builder.get_repo(code_org, settings.project_name)
    code_files = builder.get_files(settings.code_version, code_repo)
    # pass through code checker
    # test deploy
    # compare test project state file against actual state file
    # plan
    # deploy
    # validate
    pass


if __name__ == '__main__':
    main()
