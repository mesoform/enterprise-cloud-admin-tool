import os
import json
import threading
from datetime import time
from itertools import chain

from python_terraform import Terraform

from settings import SETTINGS


class TerraformDeployer(Terraform):
    def __init__(self, parsed_args, code_files, config_files, tf_code_files):
        # working directory should be unique for each deployment to prevent
        # overlapping workspaces
        working_dir = SETTINGS.WORKING_DIR_BASE / parsed_args.project_id
        self.test_dir = working_dir / parsed_args.cloud
        os.makedirs(working_dir / parsed_args.cloud, exist_ok=True)
        # write code and config files to directory
        for file_ in chain(code_files, config_files, tf_code_files):
            with open(working_dir / file_.path, "wb") as f:
                f.write(file_.decoded_content)
        super(TerraformDeployer, self).__init__(working_dir=working_dir / parsed_args.cloud, terraform_bin_path=SETTINGS.TERRAFORM_BINARY_PATH)
        self.cmd("get")  # get terraform modules
        self.init()
        # copy plugins to directory or create link
        self.cmd("workspace select" + parsed_args.project_id)
        self.current_state = self.get_state()
        self.previous_state = None

    class UnexpectedResultError(Exception):
        def __init__(self, result):
            self.message = result

    def get_plan(self, tf_vars=None, testing=False):
        if tf_vars is None:
            tf_vars = {}

        if testing:
            git_commit = "truncated_git_ref"
            tf_vars = {
                "gcp_project": "test-"
                + git_commit
                + "-"
                + str(time.hour)
                + str(time.minute),
                "disable_project": True,
            }
        return self.plan(var=tf_vars)

    def get_state(self):
        stdout = self.cmd("state pull")[1]
        return json.loads(stdout) if stdout else {}

    def run(self, testing=False, tf_vars={}):
        if testing:
            plan = self.get_plan(tf_vars, testing=True)
        else:
            plan = self.get_plan()
        self.apply(skip_plan=True, var=tf_vars)
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
        comparative_deployment_state = comparative_deployment.tfstate.__dict__
        del comparative_deployment_state["tfstate_file"]

        if json.dumps(self.current_state, sort_keys=True) != json.dumps(comparative_deployment_state, sort_keys=True):
            raise self.UnexpectedResultError('yay')


def deploy(parsed_args, code, config, tf_code):
    """
    deploy infrastructure using code and configuration supplied
    :param parsed_args: object: which contains arguments required to run code
    :param code: list: of files containing deployment code
    :param config: list: of files containing deployment configuration
    :param tf_code: list: of files containing terraform infrastructure code
    :return: boolean
    """
    real_deploy = TerraformDeployer(parsed_args, code, config, tf_code)
    # test deploy
    test_deploy = real_deploy.run(testing=True)
    # compare test project state file against actual state file
    test_deploy.read_state_file()
    real_deploy.assert_deployments_equal(test_deploy)
    # full deploy & destroy test project
    full_deployment = threading.Thread(target=real_deploy.run)
    test_deletion = threading.Thread(target=test_deploy.delete, args=(parsed_args.project_id,))
    full_deployment.start()
    test_deletion.start()
    # validate
    return real_deploy.assert_deployments_equal(real_deploy.previous_state)
