import os

from uuid import uuid4
from itertools import chain
from pathlib import Path
from unittest.mock import Mock, PropertyMock, call

import pytest

from deployer import (
    deploy,
    assert_project_id_did_not_change,
    _prepare_state_for_compare,
    WrongStateError,
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


def test_assert_project_id_did_not_change(project_state1):
    assert_project_id_did_not_change(
        project_state1["outputs"]["project_id"]["value"], project_state1
    )

    with pytest.raises(WrongStateError):
        assert_project_id_did_not_change(str(uuid4()), project_state1)


def test_deploy(
    mocker, command_line_args, code_files, config_files, short_code_config_hash
):
    """
    Checks, that when `deploy` being called:
    1) `TerraformDeployer` instantiated twice.
    2) `TerraformDeployer.run` called for two instances, and `TerraformDeployer.delete` called for test instance.
    3) No errors raised
    """
    test_deployment = Mock()
    real_deployment = Mock()

    test_deployment.current_state = {
        "serial": 1,
        "lineage": str(uuid4()),
        "some_key": 123,
    }
    # since real_deploy changes it's state twice, we use PropertyMock here to return different
    # state per __get__ invocation
    type(real_deployment).current_state = PropertyMock(
        side_effect=[
            {},
            {"serial": 2, "lineage": str(uuid4()), "some_key": 123},
            {"serial": 2, "lineage": str(uuid4()), "some_key": 123},
        ]
    )

    deployer = mocker.patch("deployer.TerraformDeployer")
    deployer.side_effect = [test_deployment, real_deployment]

    deploy(command_line_args, code_files, config_files, short_code_config_hash)

    deployer.assert_has_calls(
        [
            call(
                command_line_args,
                code_files,
                config_files,
                short_code_config_hash,
            ),
            call(command_line_args, code_files, config_files),
        ]
    )

    test_deployment.run.assert_called_once()
    test_deployment.delete.assert_called_once()
    real_deployment.run.assert_called_once()


@pytest.mark.parametrize(
    "test_state, real_state",
    [
        (
            {"serial": 1, "lineage": str(uuid4())},
            {"serial": 2, "lineage": str(uuid4())},
        ),
        (
            {"serial": 1, "lineage": str(uuid4()), "same_key": 123},
            {"serial": 2, "lineage": str(uuid4()), "same_key": 123},
        ),
        (
            {"serial": 1, "lineage": str(uuid4())},
            {"serial": 2, "lineage": str(uuid4()), "different_key": 123},
        ),
    ],
)
def test_deploy_different_states(
    mocker, command_line_args, code_files, config_files, test_state, real_state
):
    """
    Checks that wrong state leads to wrong state error.
    First case: state of test deployment equal to actual prod state, so we don't neet to deploy.
    Second case: same as first, but state contains keys, that are not cleaned by `_prepare_state_for_compare` function
    Third case: after prod deployment, if states different, then something gone wrong.
    """
    test_deployment = Mock()
    real_deployment = Mock()

    test_deployment.current_state = test_state
    real_deployment.current_state = real_state

    deployer = mocker.patch("deployer.TerraformDeployer")
    deployer.side_effect = [test_deployment, real_deployment]

    with pytest.raises(WrongStateError):
        deploy(command_line_args, code_files, config_files)
