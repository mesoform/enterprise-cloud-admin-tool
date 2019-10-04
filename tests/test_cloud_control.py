from uuid import uuid4

import pytest

from cloud_control import ArgumentsParser, CloudControl, CloudControlException


@pytest.fixture
def app_metrics_mock(mocker):
    mocker.patch("cloud_control.reporter.stackdriver.AppMetrics")


@pytest.mark.usefixtures("app_metrics_mock")
def test_deploy(mocker, command_line_args):
    deploy = mocker.patch("cloud_control.deploy")
    mocker.patch("cloud_control.common")

    cloud_control = CloudControl(command_line_args)

    cloud_control.perform_command()
    deploy.assert_called_once()


@pytest.mark.usefixtures("app_metrics_mock")
def test_config(mocker, command_line_args):
    setup = mocker.patch("cloud_control.setup")

    command_line_args.command = "config"

    cloud_control = CloudControl(command_line_args)

    cloud_control.perform_command()
    setup.assert_called_once()


@pytest.mark.usefixtures("app_metrics_mock")
def test_perform_command_exception(command_line_args):
    command_line_args.command = str(uuid4())

    cloud_control = CloudControl(command_line_args)

    with pytest.raises(CloudControlException):
        cloud_control.perform_command()


def test_argument_parser_defaults():
    command_line_args = ArgumentsParser(["-ptest", "deploy"]).args

    assert vars(command_line_args) == {
        "api_url": "https://api.github.com",
        "output_data": False,
        "code_org": "my-code-org",
        "config_org": "my-config-org",
        "project_id": "test",
        "queued_projects": None,
        "vcs_token": None,
        "config_version": "master",
        "code_version": "master",
        "key_file": None,
        "monitoring_namespace": None,
        "log_file": "/var/log/enterprise_cloud_admin.log",
        "debug": False,
        "command": "deploy",
        "force": False,
        "cloud": None,
    }
