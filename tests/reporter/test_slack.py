import textwrap

import pytest

from reporter.base import Notification
from reporter.slack import SlackNotificator, SlackNotificatorException


def test_process_args_errors(command_line_args):
    """
    Tests, that _process_args method of SlackNotificator raises
    errors, if necessary arguments for slack was not passed.
    """
    with pytest.raises(SlackNotificatorException):
        SlackNotificator(command_line_args)

    command_line_args.slack_channel = "general"

    with pytest.raises(SlackNotificatorException):
        SlackNotificator(command_line_args)


def test_send_notification(mocker, command_line_args):
    """
    Tests, that slack web client instantiated with correct credentials, and
    accepts correctly formatted message.
    """
    notification_client = mocker.patch("reporter.slack.slack").WebClient

    command_line_args.slack_channel = "general"
    command_line_args.slack_token = "token"

    notificator = SlackNotificator(command_line_args)

    # check that slack client instantiated with correct credentials
    notification_client.assert_called_once_with(
        token=command_line_args.slack_token
    )

    notificator.send_notification(
        Notification(
            message="Message",
            run_type="run_type",
            project_id="project_id",
            deployment_target="deployment_target",
            result="result",
        )
    )

    notification_client = notificator.notification_client.chat_postMessage
    notification_client.assert_called_once_with(
        channel="#general",
        text=textwrap.dedent(
            f"""\
            *Message*
            Run type: `run_type`
            Project ID: `project_id`
            Deployment on: `deployment_target`
            Result: `result`"""
        ),
    )
