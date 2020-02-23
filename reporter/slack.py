import slack

from .base import Notificator


class SlackNotificatorException(Exception):
    """
    For an errors occurred during reporting in Slack.
    """


class SlackNotificator(Notificator):
    def __init__(self, args):
        self.token = None
        self.channel = None

        super().__init__(args)

        self.notification_client = slack.WebClient(token=self.token)

    def _process_args(self, args):
        if not args.slack_token:
            raise SlackNotificatorException("You must provide slack token.")

        if not args.slack_channel:
            raise SlackNotificatorException("You must provide slack channel.")

        self.token = args.slack_token
        self.channel = args.slack_channel

    def send_message(self, message):
        self.notification_client.chat_postMessage(
            channel=f"#{self.channel}", text=message,
        )
