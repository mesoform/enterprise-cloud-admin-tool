import os
import json
import threading
from itertools import chain

from python_terraform import Terraform, TerraformCommandError as TerraformError

from settings import SETTINGS

ERROR_RETURN_CODE = 1


class DifferentStatesError(Exception):
    """
    This exception can be raised when states of some deployments does not the same.
    """


class TerraformCommandError(TerraformError):
    """
    Redefined existing terraform command error to add content of stdout and stderr.
    """

    def __str__(self):
        return f"{super().__str__()}\nSTDOUT:\n{self.out}\nSTDERR:\n{self.err}"


class TerraformDeployer(Terraform):
    def __init__(self, parsed_args, code_files, config_files, testing=False):
        self.project_id = (
            f"testing-{parsed_args.project_id}"
            if testing
            else parsed_args.project_id
        )
        self.project_dir = SETTINGS.WORKING_DIR_BASE / self.project_id

        # working directory should be unique for each deployment to prevent
        # overlapping workspaces
        self.working_dir = self.project_dir / parsed_args.cloud
        self.testing = testing

        os.makedirs(self.working_dir, exist_ok=True)

        for file_ in chain(code_files, config_files):
            with open(self.project_dir / file_.path, "wb") as f:
                f.write(file_.decoded_content)

        super(TerraformDeployer, self).__init__(
            working_dir=self.working_dir,
            terraform_bin_path=str(SETTINGS.TERRAFORM_BINARY_PATH),
        )

        self.command("get")  # get terraform modules
        self.init()

        self._create_workspace()

        self.current_state = self.get_state()
        self.previous_state = None

    def command(self, command, *args, **kwargs):
        result = self.cmd(command, *args, **kwargs)
        self._raise_if_bad_return_code(command, *result)
        return result

    def get_state(self):
        """
        Fetches the current state.
        """
        result = self.command("state pull")
        stdout = result[1]
        return json.loads(stdout) if stdout else {}

    def create_plan(self, destroy=False):
        plan_file_name = "destroy_plan" if destroy else "plan"
        plan_path = self.project_dir / plan_file_name
        skip_delete = "true" if self.testing else "false"

        plan_options = [
            "-input=false",
            f"-out={plan_path}",
            f"-var=project_id={self.project_id}",
            f"-var=project_name={self.project_id}",
            f"-var=skip_delete={skip_delete}",
        ]

        if destroy:
            plan_options.insert(0, "-destroy")

        arguments = " ".join(plan_options)
        self.command(f"plan {arguments}")

        return plan_path

    def run(self, plan=False):
        """
        Creates plan (or accepts existing) and then runs `terraform apply` command.
        Not using `Terraform.apply`, because it automatically passes `-var-file` argument,
        while plan already contain all variables.
        """
        state_before_apply = self.get_state()

        plan = self.create_plan() if not plan else plan
        apply_options = [
            "-no-color",
            "-input=false",
            "-auto-approve=false",
            str(plan),
        ]
        apply_command = f"apply {' '.join(apply_options)}"
        self.command(apply_command)

        self.previous_state = state_before_apply
        self.current_state = self.get_state()

    def delete(self):
        self.run(self.create_plan(destroy=True))

    @staticmethod
    def _raise_if_bad_return_code(command, return_code, stdout, stderr):
        if return_code == ERROR_RETURN_CODE:
            raise TerraformCommandError(return_code, command, stdout, stderr)

    def _create_workspace(self):
        """
        Check if there is existing workspace for current project,
        and recreates it if so.
        """
        workspaces_list = self.command(f"workspace list")[1]
        if self.project_id in workspaces_list:
            self.command(f"workspace select default")
            self.command(f"workspace delete -force {self.project_id}")
        self.command(f"workspace new {self.project_id}")
        self.command(f"workspace select {self.project_id}")


def assert_deployments_equal(test_state, real_state):
    """
    Compare state of test deployment against state of real deployment
    """
    keys_to_remove = ["serial", "lineage"]
    for key in keys_to_remove:
        del test_state[key]
        del real_state[key]

    if test_state != real_state:
        raise DifferentStatesError(
            f"\nCurrent state:\n{test_state}\n\nDeployment state:\n{real_state}"
        )


def deploy(parsed_args, code, config):
    """
    deploy infrastructure using code and configuration supplied
    :param parsed_args: object: which contains arguments required to run code
    :param code: list: of files containing deployment code
    :param config: list: of files containing deployment configuration
    :return: boolean
    """
    test_deployer = TerraformDeployer(parsed_args, code, config, testing=True)
    real_deployer = TerraformDeployer(parsed_args, code, config)

    test_deployment = threading.Thread(target=test_deployer.run)
    real_deployment = threading.Thread(target=real_deployer.run)
    test_deployment_deletion = threading.Thread(target=test_deployer.delete)

    test_deployment.run()
    real_deployment.run()
    test_deployment_deletion.run()

    assert_deployments_equal(
        test_deployer.current_state, real_deployer.current_state
    )
    print("Success!")
