#!/usr/bin/env python
from __future__ import print_function, absolute_import

import json
from python_terraform import Terraform
import os
import builder


MODULE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_BRANCH = 'master'
DEFAULT_CODE_BRANCH = 'master'
WORKING_DIR_BASE = '/tmp'


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


def setup_tf_env(settings, code_files, config_files):
    working_dir = WORKING_DIR_BASE + settings.project_id
    os.mkdir(working_dir)
    # write code and config files to directory
    for file_ in code_files:
        with open(working_dir + file_) as f:
            f.write(file_.content)
    for file_ in config_files:
        with open(working_dir + file_) as f:
            f.write(file_.content)

    tf = Terraform(working_dir=working_dir)
    tf.cmd('get')  # get terraform modules
    # copy plugins to directory or create link
    return tf


def tf_plan():
    pass


def tf_apply():
    pass


def tf_destroy():
    pass


def tidy_up():
    pass


def delete_test_project():
    pass


def retry_tf_apply():
    pass


def main():
    settings = add_args()
    # needs to differentiate between orgs and repo for code and config
    config_org = builder.get_org(settings)
    config_files = builder.get_files(config_org, settings.project_name, settings.cloud settings.config_version)
    # pull args.tf_code_version (default = master)
    # pull files from args.branch
    code_org = builder.get_org(settings)
    code_files = builder.get_files(code_org, settings.project_name, settings.cloud settings.config_version)
    # pass through code checker
    # test deploy
    # compare test project state file against actual state file
    # plan
    # deploy
    # validate
    pass


if __name__ == '__main__':
    main()
