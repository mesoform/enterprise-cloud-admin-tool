import os
import json
import threading
from itertools import chain

from python_terraform import Terraform, TerraformCommandError as TerraformError

from settings import SETTINGS

ERROR_RETURN_CODE = 1


class DifferentStatedError(Exception):
    def __init__(self, result):
        self.message = result


class TerraformCommandError(TerraformError):
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

        self.cmd("get")  # get terraform modules
        self.init()

        # copy plugins to directory or create link
        self.cmd(f"workspace new {self.project_id}")
        self.cmd(f"workspace select {self.project_id}")
        self.current_state = self.get_state()
        self.previous_state = None

    def cmd(self, command, *args, **kwargs):
        result = super().cmd(command, *args, **kwargs)
        self._raise_if_bad_return_code(command, *result)
        return result

    def get_plan(self):
        """
        Invokes `terraform plan` with `-out` argument. As a result, we have state
        stored in a file.
        """
        plan_path = self.project_dir / "plan"

        plan_options = [
            f"-out={plan_path}",
            f"-var=project_id={self.project_id}",
            f"-var=project_name={self.project_id}",
            f"-var=skip_delete={'true' if self.testing else 'false'}",
        ]
        arguments = " ".join(plan_options)
        self.cmd("plan -input=false " + arguments)
        return plan_path

    def get_state(self):
        """
        Fetches the current state.
        """
        result = self.cmd("state pull")
        stdout = result[1]
        return json.loads(stdout) if stdout else {}

    def run(self, plan=False):
        """
        Creates plan (or accepts existing) and then runs `terraform apply` command.
        Not using `Terraform.apply`, because it automatically passes `-var-file` argument,
        while plan already contain all variables.
        """
        state_before_apply = self.get_state()

        plan = self.get_plan() if not plan else plan
        apply_command = (
            f"apply -no-color -input=false -auto-approve=false {plan}"
        )
        self.cmd(apply_command)

        self.previous_state = state_before_apply
        self.current_state = self.get_state()

    def get_destroy_plan(self):
        plan_path = self.project_dir / "destroy_plan"
        skip_delete = "true" if self.testing else "false"
        plan_options = [
            f"-out={plan_path}",
            f"-var=project_id={self.project_id}",
            f"-var=project_name={self.project_id}",
            f"-var=skip_delete={skip_delete}",
        ]
        arguments = " ".join(plan_options)
        self.cmd("plan -destroy -input=false " + arguments)
        return plan_path

    def delete(self):
        self.run(self.get_destroy_plan())

    @staticmethod
    def _raise_if_bad_return_code(command, return_code, stdout, stderr):
        if return_code == ERROR_RETURN_CODE:
            raise TerraformCommandError(return_code, command, stdout, stderr)


def assert_deployments_equal(test_state, real_state):
    """
    Compare state of test deployment against state of real deployment
    """
    keys_to_remove = ["serial", "lineage"]
    for key in keys_to_remove:
        del test_state[key]
        del real_state[key]

    if test_state != real_state:
        raise DifferentStatedError(
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
