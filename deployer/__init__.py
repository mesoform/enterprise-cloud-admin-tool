#!/usr/bin/env python
from __future__ import print_function, absolute_import

import json
from python_terraform import Terraform
import os
import threading
from datetime import time

MODULE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_DIR_BASE = '/tmp'


def tf_setup(settings, code_files, config_files):
    # working directory should be unique for each deployment to prevent
    # overlapping workspaces
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
    tf.cmd('workspace select' + settings.project_id)
    return tf


def get_plan(terraform_instance, tf_vars=None, testing=False):
    if testing:
        git_commit = 'truncated_git_ref'
        tf_vars = {
            'gcp_project': 'test-' + git_commit + '-' + str(time.hour) +
                           str(time.minute),
            'disable_project': True
        }
    return terraform_instance.plan(tf_vars)


def get_state(terraform_instance):
    return json.loads(terraform_instance.cmd('state pull'))


def tf_apply(terraform_instance, testing=False, tf_vars=None):
    if testing:
        plan = get_plan(terraform_instance, tf_vars, testing=True)
    else:
        plan = get_plan(terraform_instance)
    terraform_instance.apply(dir_or_plan=plan)
    return terraform_instance.read_state_file()


def tf_destroy():
    pass


def __tidy_up():
    pass


def delete_test_project(terraform_instance, project_id):
    return_code, std_out, std_err = terraform_instance.destroy(project_id)
    if return_code is not 200:
        return False, std_err
    return True


def __retry_tf_apply():
    pass


def compare_deployments(current_deployment, new_deployment):
    if current_deployment == new_deployment:
        return True
    return False


def deploy(settings, config, code):
    terraform_instance = tf_setup(settings, code, config)
    # test deploy
    test_deployment = tf_apply(terraform_instance, testing=True)
    # compare test project state file against actual state file
    compare_deployments(test_deployment, settings.project_id)
    # full deploy & destroy test project
    full_deployment = threading.Thread(
        target=tf_apply)
    test_deletion = threading.Thread(
        target=delete_test_project)
    full_deployment.start()
    test_deletion.start()
    # validate
    pass
