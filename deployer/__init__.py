#!/usr/bin/env python
from __future__ import print_function, absolute_import

import json
from python_terraform import Terraform
import os
import threading
from datetime import time

MODULE_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_DIR_BASE = '/tmp'


class TerraformDeployer(Terraform):
    def __init__(self, settings, code_files, config_files):
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
        super(TerraformDeployer, self).__init__(working_dir=working_dir)
        self.cmd('get')  # get terraform modules
        # copy plugins to directory or create link
        self.cmd('workspace select' + settings.project_id)
        self.current_state = self.get_state()
        self.previous_state = None

    class UnexpectedResultError(Exception):
        def __init__(self, result):
            self.message = result

    def get_plan(self, tf_vars=None, testing=False):
        if testing:
            git_commit = 'truncated_git_ref'
            tf_vars = {
                'gcp_project': 'test-' + git_commit + '-' + str(time.hour) +
                               str(time.minute),
                'disable_project': True
            }
        return self.plan(tf_vars)

    def get_state(self):
        return json.loads(self.cmd('state pull'))

    def run(self, testing=False, tf_vars=None):
        if testing:
            plan = self.get_plan(tf_vars, testing=True)
        else:
            plan = self.get_plan()
        self.apply(dir_or_plan=plan)
        return self

    def __tidy_up(self):
        pass

    def delete(self, project_id):
        return_code, std_out, std_err = self.destroy(project_id)
        if return_code is not 200:
            return False, std_err
        return True

    @staticmethod
    def __retry_tf_apply():
        pass

    def assert_deployments_equal(self, comparative_deployment):
        """
        Compare the known state of the current environment to another
        :param comparative_deployment:  dict: of state file for first
            comparative_deployment
        :return: boolean
        """
        result = \
            set(self.current_state.items()) ^ \
            set(comparative_deployment.items())
        if result is None:
            return True
        return self.UnexpectedResultError(result)


def deploy(settings, code, config):
    """
    deploy infrastructure using code and configuration supplied
    :param settings: object: which contains arguments required to run code
    :param code: list: of files containing deployment code
    :param config: list: of files containing deployment configuration
    :return: boolean
    """
    real_deploy = TerraformDeployer(settings, code, config)
    # test deploy
    test_deploy = real_deploy.run(testing=True)
    # compare test project state file against actual state file
    real_deploy.assert_deployments_equal(test_deploy.read_state_file())
    # full deploy & destroy test project
    full_deployment = threading.Thread(target=real_deploy.run)
    test_deletion = threading.Thread(target=test_deploy.delete)
    full_deployment.start()
    test_deletion.start()
    # validate
    return real_deploy.assert_deployments_equal(real_deploy.previous_state)
