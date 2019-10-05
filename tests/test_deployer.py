import os

from uuid import uuid4
from itertools import chain
from pathlib import Path
from unittest.mock import Mock

import pytest

from deployer import (
    deploy,
    _prepare_state_for_compare,
    DifferentStatesError,
    TerraformDeployer,
    TerraformCommandError,
)


@pytest.fixture
def terraform_deployer(
    mocker, working_directory, command_line_args, code_files, config_files
):
    mocker.patch.dict(
        "settings.SETTINGS.attributes",
        {"WORKING_DIR_BASE": Path(working_directory.strpath)},
    )
    deployer = TerraformDeployer(command_line_args, code_files, config_files)
    yield deployer
    deployer.cmd(f"workspace delete {deployer.project_id}")


def test_terraform_deployer_init(terraform_deployer):
    """
    Verify that deployer instance after instantiation has empty state.
    """
    assert terraform_deployer.current_state == {}


def test_terraform_deployer_init_creates_all_files(
    terraform_deployer, code_files, config_files
):
    """
    Deployer instantiation results in a set of created .tf and .json files in the working directory.
    """
    for file in chain(code_files, config_files):
        assert os.path.exists(terraform_deployer.working_dir / file.name)


def test_terraform_deployer_init_creates_workspace(terraform_deployer):
    """
    Terraform deployer init should prepare workspace.
    """
    assert (
        terraform_deployer.project_id
        in terraform_deployer.command("workspace list")[1]
    )


def test_command_throws_error(terraform_deployer):
    """
    If terraform subprocess returns error code, we throw error with detailed info.
    """
    terraform_deployer.cmd = Mock(return_value=(1, "", ""))
    with pytest.raises(TerraformCommandError):
        terraform_deployer.get_state()


def test_get_state(terraform_deployer):
    """
    Initial state should be empty.
    """
    assert terraform_deployer.get_state() == {}


@pytest.mark.usefixtures("google_credentials")
def test_create_plan(terraform_deployer):
    """
    Tests, that create_plan method creates plan file in project dir.
    """
    terraform_deployer.create_plan()
    assert os.path.exists(terraform_deployer.project_dir / "plan")


def test_create_destroy_plan(terraform_deployer):
    """
    Tests, that create_plan method with destroy option creates plan file in project dir.
    """
    terraform_deployer.command = Mock(side_effect=terraform_deployer.command)
    terraform_deployer.create_plan(destroy=True)
    assert "-destroy" in terraform_deployer.command.call_args[0][0]
    assert os.path.exists(terraform_deployer.project_dir / "destroy_plan")


def test_run_changes_state(terraform_deployer):
    """
    `run` invocation changes state, so we should check that.
    """
    terraform_deployer.command = Mock()
    terraform_deployer.get_state = lambda: str(uuid4())
    terraform_deployer.run()
    assert terraform_deployer.previous_state != terraform_deployer.current_state


def test_run_calls_apply(terraform_deployer):
    """
    `run` should invoke `terraform apply` with correct arguments.
    """
    terraform_deployer.get_state = Mock()
    terraform_deployer.command = Mock()

    plan = "some_plan"
    terraform_deployer.run(plan=plan)
    terraform_deployer.command.assert_called_with(
        f"apply -no-color -input=false -auto-approve=false {plan}"
    )


def test_delete(terraform_deployer):
    """
    `delete` should call run with generated destruction plan.
    """
    terraform_deployer.run = Mock()
    terraform_deployer.delete()
    terraform_deployer.run.assert_called_with(
        terraform_deployer.project_dir / "destroy_plan"
    )


def test_prepare_state_for_compare(project_state1, project_state2):
    """
    Tests that states being cleaned properly.
    """
    assert _prepare_state_for_compare(
        project_state1
    ) == _prepare_state_for_compare(project_state2)


def test_deploy(mocker, command_line_args, code_files, config_files):
    """
    Checks, that when `deploy` bein called, `TerraformDeployer.run` called
    for two instances, and `TerraformDeployer.delete` called for test instance.
    """
    test_deployment = Mock()
    real_deployment = Mock()

    test_deployment.current_state = {"serial": 1, "lineage": str(uuid4())}
    real_deployment.current_state = {"serial": 2, "lineage": str(uuid4())}

    deployer = mocker.patch("deployer.TerraformDeployer")
    deployer.side_effect = [test_deployment, real_deployment]
    deploy(command_line_args, code_files, config_files)

    test_deployment.run.assert_called_once()
    test_deployment.delete.assert_called_once()
    real_deployment.run.assert_called_once()


def test_deploy_different_states(
    mocker, command_line_args, code_files, config_files
):
    """
    Checks that state of deployer instance changes from deploy to deploy.
    """
    test_deployment = Mock()
    real_deployment = Mock()

    test_deployment.current_state = {"serial": 1, "lineage": str(uuid4())}
    real_deployment.current_state = {
        "serial": 2,
        "lineage": str(uuid4()),
        "different_element": True,
    }

    deployer = mocker.patch("deployer.TerraformDeployer")
    deployer.side_effect = [test_deployment, real_deployment]

    with pytest.raises(DifferentStatesError):
        deploy(command_line_args, code_files, config_files)
