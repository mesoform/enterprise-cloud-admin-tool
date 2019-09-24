import os

from itertools import chain
from pathlib import Path
from unittest.mock import patch

import pytest

from deployer import TerraformDeployer


@pytest.fixture(scope="session")
def working_directory(tmpdir_factory):
    return tmpdir_factory.mktemp("data")


@pytest.fixture(scope="session")
def terraform_deployer(
    working_directory, command_line_args, code_files, config_files
):
    with patch.dict(
        "settings.SETTINGS.attributes",
        {"WORKING_DIR_BASE": Path(working_directory.strpath)},
    ):
        return TerraformDeployer(command_line_args, code_files, config_files)


def test_terraform_deployer_init_creates_all_files(
    working_directory, command_line_args, code_files, config_files
):
    """
    Deployer instantiation results in a set of created .tf and .json files in the working directory.
    """
    with patch.dict(
        "settings.SETTINGS.attributes",
        {"WORKING_DIR_BASE": Path(working_directory.strpath)},
    ):
        deployer = TerraformDeployer(
            command_line_args, code_files, config_files
        )
        for file in chain(code_files, config_files):
            assert os.path.exists(deployer.working_dir / file.name)


def test_terraform_deployer_init(terraform_deployer):
    """
    Verify that deployer instance after instantiation has empty state.
    """
    assert terraform_deployer.current_state == {}


def test_get_plan(terraform_deployer):
    """
    Tests, that get_plan method creates plan file in project dir.
    """
    terraform_deployer.get_plan()
    assert os.path.exists(terraform_deployer.project_dir / "plan")


def test_run(terraform_deployer):
    terraform_deployer.run()
    assert terraform_deployer.current_state
    assert terraform_deployer.previous_state == {}
