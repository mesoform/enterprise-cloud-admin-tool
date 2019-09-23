import os
import json
import threading
from itertools import chain

from python_terraform import Terraform

from settings import SETTINGS

ERROR_EXIT_CODE = 1


class DifferentStatedError(Exception):
    def __init__(self, result):
        self.message = result


class BadExitCodeError(Exception):
    def __init__(self, exit_code, stdout, stderr):
        self.message = f"""
        Command failed.
        exit_code: {exit_code}
        stdout: {stdout}
        stderr: {stderr}
        """


class TerraformDeployer(Terraform):
    def __init__(self, parsed_args, code_files, config_files):
        # working directory should be unique for each deployment to prevent
        # overlapping workspaces
        self.project_id = parsed_args.project_id
        self.project_dir = SETTINGS.WORKING_DIR_BASE / parsed_args.project_id
        os.makedirs(self.project_dir / parsed_args.cloud, exist_ok=True)

        for file_ in chain(code_files, config_files):
            with open(self.project_dir / file_.path, "wb") as f:
                f.write(file_.decoded_content)

        super(TerraformDeployer, self).__init__(
            working_dir=self.project_dir / parsed_args.cloud, terraform_bin_path=str(SETTINGS.TERRAFORM_BINARY_PATH)
        )

        self.cmd("get")  # get terraform modules
        self.init()

        # copy plugins to directory or create link
        self.cmd(f"workspace new {parsed_args.project_id}")
        self.cmd(f"workspace select {parsed_args.project_id}")
        self.current_state = self.get_state()
        self.previous_state = None

    def get_plan(self):
        """
        Invokes `terraform plan` with `-out` argument. As a result, we have state
        stored in a file.
        """
        plan_path = self.project_dir / "plan"
        self._raise_if_bad_exit_code(*self.plan(f"-out={plan_path}"))
        return plan_path

    def get_state(self):
        """
        Fetches the current state.
        """
        result = self.cmd("state pull")
        self._raise_if_bad_exit_code(*result)
        stdout = result[1]
        return json.loads(stdout) if stdout else {}

    def run(self):
        """
        Creates plan and then runs `terraform apply` command.
        Not using `Terraform.apply`, because it automatically passes `-var-file` argument,
        while plan already contain all variables.
        """
        state_before_apply = self.get_state()

        plan = self.get_plan()
        apply_command = f"apply -no-color -input=false -auto-approve=false {plan}"
        self.cmd(apply_command)

        self.previous_state = state_before_apply
        self.current_state = self.get_state()

        return self

    def delete(self):
        result = self.destroy(self.project_id)
        self._raise_if_bad_exit_code(*result)
        return True

    @staticmethod
    def _raise_if_bad_exit_code(exit_code, stdout, stderr):
        if exit_code == ERROR_EXIT_CODE:
            raise BadExitCodeError(exit_code, stdout, stderr)


def assert_deployments_equal(test_state, real_state):
    """
    Compare state of test deployment against state of real deployment
    """
    if test_state != real_state:
        raise DifferentStatedError(
            f"Current state: {test_state}\nDeployment state: {real_state}"
        )


def deploy(parsed_args, code, config):
    """
    deploy infrastructure using code and configuration supplied
    :param parsed_args: object: which contains arguments required to run code
    :param code: list: of files containing deployment code
    :param config: list: of files containing deployment configuration
    :return: boolean
    """
    test_deploy = TerraformDeployer(parsed_args, code, config)
    real_deploy = TerraformDeployer(parsed_args, code, config)

    threading.Thread(target=test_deploy.run)
    threading.Thread(target=real_deploy.run)

    threading.Thread(target=test_deploy.delete)

    return assert_deployments_equal(test_deploy.current_state, real_deploy.current_state)
