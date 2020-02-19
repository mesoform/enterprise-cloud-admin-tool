import slack

from .base import Logger


class SlackLoggerException(Exception):
    """
    For an errors occurred during reporting in Slack.
    """


class SlackLogger(Logger):
    def __init__(self, args):
        self.token = None
        self.channel = None

        super().__init__(args)

        self.logging_client = slack.WebClient(token=self.token)

    def _process_args(self, args):
        if not args.slack_token:
            raise SlackLoggerException("You must provide slack token.")

        if not args.slack_channel:
            raise SlackLoggerException("You must provide slack channel.")

        self.token = args.slack_token
        self.channel = args.slack_channel

    def send_message(self, message):
        self.logging_client.chat_postMessage(
            channel=f"#{self.channel}", text=message,
        )
