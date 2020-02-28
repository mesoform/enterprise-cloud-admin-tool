import textwrap

import slack

from .base import Notification, Notifier


class SlackNotifierException(Exception):
    """
    For an errors occurred during reporting in Slack.
    """


class SlackNotifier(Notifier):
    def __init__(self, args):
        self.token = None
        self.channel = None

        super().__init__(args)

        self.notification_client = slack.WebClient(token=self.token)

    def _process_args(self, args):
        if not args.slack_token:
            raise SlackNotifierException("You must provide slack token.")

        if not args.slack_channel:
            raise SlackNotifierException("You must provide slack channel.")

        self.token = args.slack_token
        self.channel = args.slack_channel

    def _send_notification(self, notification_text: str):
        self.notification_client.chat_postMessage(
            channel=f"#{self.channel}", text=notification_text,
        )

    def _get_notification_text(self, notification: Notification) -> str:
        notification_text = textwrap.dedent(
            f"""\
            *{notification.message}*
            Run type: `{notification.run_type}`
            Project ID: `{notification.project_id}`
            Deployment on: `{notification.deployment_target}`
            """
        )
        if notification.result is not None:
            notification_text += f"Result: `{notification.result}`"

        return notification_text
