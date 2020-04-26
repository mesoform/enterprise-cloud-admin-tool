import copy

from unittest.mock import Mock

import pytest

from cloud_control import ArgumentsParser, CloudControl, CloudControlException
from reporter.slack import SlackNotifier
from reporter.stackdriver import StackdriverMetrics


@pytest.fixture
def cli_args_with_mocked_metrics(command_line_args):
    args = copy.copy(command_line_args)
    args.monitoring_system = Mock()
    args.monitoring_system.return_value.app_runtime.total_seconds.return_value = (
        450.45
    )
    return args


def test_deploy(
    mocker, cli_args_with_mocked_metrics, sha256_hash, short_code_config_hash
):
    deploy = mocker.patch("cloud_control.deploy")
    common = mocker.patch("cloud_control.common")
    common.get_hash_of_latest_commit.return_value = sha256_hash

    cloud_control = CloudControl(cli_args_with_mocked_metrics)

    cloud_control.perform_command()
    deploy.assert_called_once_with(
        cli_args_with_mocked_metrics,
        common.get_files(),
        common.get_files(),
        short_code_config_hash,
    )
    cli_args_with_mocked_metrics.monitoring_system.return_value.send_metrics.assert_called_once()


def test_config(mocker, cli_args_with_mocked_metrics):
    setup = mocker.patch("cloud_control.setup")

    cli_args_with_mocked_metrics.command = "config"

    cloud_control = CloudControl(cli_args_with_mocked_metrics)

    cloud_control.perform_command()
    setup.assert_called_once()
    cli_args_with_mocked_metrics.monitoring_system.return_value.send_metrics.assert_called_once()


def test_perform_command_exception(cli_args_with_mocked_metrics):
    cli_args_with_mocked_metrics.command = "check"

    cloud_control = CloudControl(cli_args_with_mocked_metrics)

    with pytest.raises(CloudControlException):
        cloud_control.perform_command()


def test_argument_parser_defaults(tmpdir):
    token = tmpdir.join("some_token.json")
    token.write("content")

    command_line_args = ArgumentsParser(
        [
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
            "--monitoring-system",
            "stackdriver",
            "--notification-system",
            "slack",
            "--disable-local-reporter",
            "--json-logging",
            "deploy",
            "test",
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
        "code_org": "my-code-org",
        "config_org": "my-config-org",
        "code_repo": "testrepo1",
        "config_repo": "testrepo2",
        "project_id": "test",
        "vcs_token": "e750dcf1c15273dfc687049f6dfcb38d970e0547",
        "config_version": "master",
        "code_version": "master",
        "disable_local_reporter": True,
        "json_logging": True,
        "monitoring_namespace": "random-monitoring-project",
        "monitoring_system": StackdriverMetrics,
        "notification_system": SlackNotifier,
        "slack_channel": None,
        "slack_token": None,
        "log_file": "/var/log/enterprise_cloud_admin.log",
        "metrics_file": "/var/log/enterprise_cloud_admin_metrics",
        "debug": False,
        "command": "deploy",
        "force": False,
        "cloud": "gcp",
        "vcs_platform": "github",
    }
