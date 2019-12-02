from uuid import uuid4

import pytest

from cloud_control import ArgumentsParser, CloudControl, CloudControlException


@pytest.fixture
def stackdriver_mock(mocker):
    mocker.patch("cloud_control.common.GcpAuth")
    return mocker.patch("cloud_control.StackdriverMetrics")


def test_deploy(
    mocker,
    command_line_args,
    sha256_hash,
    short_code_config_hash,
    stackdriver_mock,
):
    deploy = mocker.patch("cloud_control.deploy")
    common = mocker.patch("cloud_control.common")
    common.get_hash_of_latest_commit.return_value = sha256_hash

    cloud_control = CloudControl(command_line_args)

    cloud_control.perform_command()
    deploy.assert_called_once_with(
        command_line_args,
        common.get_files(),
        common.get_files(),
        short_code_config_hash,
    )
    stackdriver_mock.return_value.send_metrics.assert_called_once()


def test_config(mocker, command_line_args, stackdriver_mock):
    setup = mocker.patch("cloud_control.setup")

    command_line_args.command = "config"

    cloud_control = CloudControl(command_line_args)

    cloud_control.perform_command()
    setup.assert_called_once()
    stackdriver_mock.return_value.send_metrics.assert_called_once()


@pytest.mark.usefixtures("stackdriver_mock")
def test_perform_command_exception(command_line_args):
    command_line_args.command = str(uuid4())

    cloud_control = CloudControl(command_line_args)

    with pytest.raises(CloudControlException):
        cloud_control.perform_command()


def test_argument_parser_defaults(tmpdir):
    token = tmpdir.join("some_token.json")
    token.write("content")

    command_line_args = ArgumentsParser(
        [
            "-p",
            "test",
            "-o",
            "my-code-org",
            "-O",
            "my-config-org",
            "--key-file",
            token.strpath,
            "--vcs-token",
            "e750dcf1c15273dfc687049f6dfcb38d970e0547",
            "--monitoring-namespace",
            "random-monitoring-project",
            "--disable-local-reporter",
            "--json-logging",
            "deploy",
            "--cloud",
            "gcp",
            "--code-repo",
            "testrepo1",
            "--config-repo",
            "testrepo2",
        ]
    ).args

    command_line_args_dict = vars(command_line_args)

    assert command_line_args_dict.pop("key_file").name == token.strpath

    assert command_line_args_dict == {
        "api_url": "https://api.github.com",
        "output_data": False,
        "code_org": "my-code-org",
        "config_org": "my-config-org",
        "code_repo": "testrepo1",
        "config_repo": "testrepo2",
        "project_id": "test",
        "queued_projects": None,
        "vcs_token": "e750dcf1c15273dfc687049f6dfcb38d970e0547",
        "config_version": "master",
        "code_version": "master",
        "disable_local_reporter": True,
        "json_logging": True,
        "monitoring_namespace": "random-monitoring-project",
        "log_file": "/var/log/enterprise_cloud_admin.log",
        "debug": False,
        "command": "deploy",
        "force": False,
        "cloud": "gcp",
    }
