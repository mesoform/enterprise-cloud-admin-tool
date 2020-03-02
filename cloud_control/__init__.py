import argparse
from datetime import datetime
from typing import Union

import common

from code_control import setup, BranchProtectArgAction
from deployer import deploy

from reporter.local import get_logger, LocalMetrics
from reporter.base import MetricsRegistry, Metrics, Notification

from reporter.slack import SlackNotifier

from reporter.stackdriver import StackdriverMetrics
from reporter.cloudwatch import CloudWatchMetrics

from settings import SETTINGS


class CloudControlException(Exception):
    pass


class NotificationException(CloudControlException):
    pass


class MonitoringException(CloudControlException):
    pass


class NotificationSystemArgAction(argparse.Action):
    """
    Converts "notification-system" cli argument to instance of Metrics
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if values == "slack":
            notification_system = SlackNotifier
        else:
            raise NotificationException(
                f"Integration with '{values}' notification system is not implemented yet."
            )

        setattr(namespace, self.dest, notification_system)


class MonitoringSystemArgAction(argparse.Action):
    """
    Converts "monitoring-system" cli argument to instance of Metrics
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        if nargs is not None:
            raise ValueError("nargs not allowed")
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if values == "stackdriver":
            monitoring_system = StackdriverMetrics
        elif values == "cloudwatch":
            monitoring_system = CloudWatchMetrics
        else:
            raise MonitoringException(
                f"Integration with '{values}' monitoring system is not implemented yet."
            )

        setattr(namespace, self.dest, monitoring_system)


class ArgumentsParser:
    """
    That class used for subparsers setup, and storing all parsed arguments.
    """

    def __init__(self, args=None):
        self.root_parser = common.root_parser()

        self.root_parser.add_argument(
            "--notification-system",
            help="notification system, such as GCP Stackdriver, AWS CloudWatch, or Slack",
            action=NotificationSystemArgAction,
            choices=["slack"],
        )
        self.root_parser.add_argument(
            "--monitoring-system",
            help="monitoring system for metrics, such as GCP Stackdriver, AWS CloudWatch, "
            "Zabbix, etc.",
            action=MonitoringSystemArgAction,
            choices=["stackdriver", "cloudwatch", "zabbix"],
        )

        self.management_parser = self.root_parser.add_subparsers(
            help="manage infrastructure deployment or infrastructure"
            " configuration",
            dest="command",
        )
        self._setup_deploy_parser()
        self._setup_config_parser()

        self.args = self.root_parser.parse_args(args)

        if not self.args.config_repo:
            self.args.config_repo = self.args.project_id

    def _setup_deploy_parser(self):
        """
        Setup specific to deploy command arguments
        """
        deploy_parser = self.management_parser.add_parser(
            "deploy", help="deploy configuration to the cloud"
        )
        deploy_parser.formatter_class = argparse.RawTextHelpFormatter

        deploy_parser.add_argument(
            "project_id",
            help="ID of project we're deploying changes for",
            default=SETTINGS.DEFAULT_PROJECT_NAME,
        )
        deploy_parser.add_argument(
            "--cloud",
            choices=["all"] + SETTINGS.SUPPORTED_CLOUDS,
            default="gcp",
        )
        deploy_parser.add_argument(
            "--code-repo",
            help="Name of the repository with terraform infrastructure code",
            required=True,
        )
        deploy_parser.add_argument(
            "--config-repo",
            help="Name of the repository with terraform variables files. "
            "Overrides project-id for the name of the repository where "
            "to store the project's infrastructure configuration. "
            "We recommend using project-id for the name of the config "
            "repository as well to maintain consistent naming but if "
            "you need to call it something else, use this argument",
        )

    def _setup_config_parser(self):
        """
        Setup specific to config command arguments
        """
        config_parser = self.management_parser.add_parser(
            "config",
            help="Administer cloud configuration on respective repository",
        )
        config_parser.set_defaults(
            change_files=SETTINGS.LOCAL_FILES,
            branch_permissions=SETTINGS.PROTECTED_BRANCH,
            force=False,
        )
        config_parser.formatter_class = argparse.RawTextHelpFormatter

        config_parser.add_argument("--github")
        config_parser.add_argument(
            "c_action", choices=("create", "delete", "update")
        )
        config_parser.add_argument(
            "project_id",
            help="ID of project we're creating a repository for",
            default=SETTINGS.DEFAULT_PROJECT_NAME,
        )
        config_parser.add_argument(
            "--config-repo",
            help="Name of the repository with terraform variables files. "
            "Overrides project-id for the name of the repository where "
            "to store the project's infrastructure configuration. "
            "We recommend using project-id for the name of the config "
            "repository as well to maintain consistent naming but if "
            "you need to call it something else, use this argument",
        )
        config_parser.add_argument(
            "--branch-protection",
            choices=("standard", "high"),
            help="\nThe level to which the branch will be "
            "protected\n"
            "standard: adds review requirements, stale reviews"
            " and admin enforcement\n"
            "high: also code owner reviews and review count",
            default="standard",
            action=BranchProtectArgAction,
        )
        config_parser.add_argument(
            "--bypass-branch-protection",
            help="Bypasses branch protection when updating files"
            " which already exist in the repository",
            default=False,
            action="store_true",
        )
        config_parser.add_argument(
            "-f",
            "--force",
            help="Force actions on preexisting repo",
            default=False,
            action="store_true",
        )
        config_parser.add_argument(
            "--output-data",
            help="Output repo data to files in "
            + str(SETTINGS.PROJECT_DATA_DIR),
            action="store_true",
        )


class CloudControl:
    """
    Entry point. Calls specific command passed to cli-app.
    """

    CLOUD_NAME_MAP = {
        "gcp": "Google Cloud Platform",
        "aws": "Amazon Web Services",
        "github": "Github",
    }

    def __init__(self, args):
        self.args = args

        if self.args.vcs_platform == "all":
            raise CloudControlException(
                "Choosing of all VCS platforms is not implemented currently."
            )

        if self.args.command == "deploy" and self.args.cloud == "all":
            raise CloudControlException(
                "Choosing of all clouds is not implemented currently."
            )

        self._setup_logger()
        self.metrics_registry = MetricsRegistry(args.command)
        self.metrics_registry.add_metric("total", 1)
        self._local_metrics = None
        self._remote_metrics = None
        self._notification_system = None

        self.local_metrics = LocalMetrics(self.args)

        if self.args.monitoring_system:
            self.remote_metrics = self.args.monitoring_system(self.args)

        if self.args.notification_system:
            self.notification_system = self.args.notification_system(self.args)

    def _setup_logger(self):
        self._log = get_logger(
            __name__,
            log_file=self.args.log_file,
            debug=self.args.debug,
            json_formatter=self.args.json_logging,
        )

    @property
    def remote_metrics(self) -> Metrics:
        return self._remote_metrics

    @remote_metrics.setter
    def remote_metrics(self, value: Metrics):
        self._remote_metrics = value

    @property
    def local_metrics(self) -> Metrics:
        return self._local_metrics

    @local_metrics.setter
    def local_metrics(self, value: Metrics):
        self._local_metrics = value

    @property
    def notification_system(self) -> Union[SlackNotifier]:
        return self._notification_system

    @notification_system.setter
    def notification_system(self, value: Union[SlackNotifier]):
        self._notification_system = value

    def _log_and_send_metrics(self, command, success):
        self._log.info("finished " + command + " run")

        self.metrics_registry.add_metric("successes", int(success))
        self.metrics_registry.add_metric("failures", int(not success))

        end_time = datetime.utcnow()
        if self.remote_metrics is not None:
            self.remote_metrics.end_time = end_time

            self.metrics_registry.add_metric(
                "time", self.remote_metrics.app_runtime.total_seconds()
            )

            self.remote_metrics.metrics_registry = self.metrics_registry
            self.remote_metrics.send_metrics()

        if not self.args.disable_local_reporter:
            if self.metrics_registry.metrics["time"]["value"] is None:
                self.local_metrics.end_time = end_time
                self.metrics_registry.add_metric(
                    "time", self.local_metrics.app_runtime.total_seconds()
                )

            self.local_metrics.metrics_registry = self.metrics_registry
            self.local_metrics.send_metrics()

        self._send_notification(
            "Finished new run.", "success" if success else "failure"
        )

    def perform_command(self):
        """
        Checks that passed command implemented in entry point class,
        runs it, logs that command was runned and sends metrics.
        """

        if self.args.command == "deploy":
            command = self._deploy
        elif self.args.command == "config":
            command = self._config
        else:
            raise CloudControlException(
                "Command {} does not implemented".format(self.args.command)
            )

        self._send_notification("Started new run.")

        success = False
        try:
            success = command()
        finally:
            self._log_and_send_metrics(self.args.command, success)

    def _send_notification(self, message, result=None):
        """
        If notification system enabled, collects required information and
        sends notification.
        """
        if self.notification_system:
            deployment_target = (
                self.CLOUD_NAME_MAP[self.args.cloud]
                if self.args.command == "deploy"
                else self.CLOUD_NAME_MAP[self.args.vcs_platform]
            )

            notification = {
                "message": message,
                "run_type": self.args.command,
                "project_id": self.args.project_id,
                "deployment_target": deployment_target,
            }
            if result is not None:
                notification["result"] = result

            self.notification_system.send_notification(
                Notification(**notification)
            )

    def _deploy(self):
        self._log.info("Starting deployment")
        if self.args.cloud == "all":
            self.args.cloud = "all_"
        config_org = common.get_org(self.args, self.args.config_org)
        code_org = common.get_org(self.args, self.args.code_org)
        config_files = common.get_files(
            config_org,
            self.args.config_repo,
            self.args.cloud,
            self.args.config_version,
        )
        # code repo should contain any lists or maps that define
        # security policies
        # and operating requirements. The code repo should be public.
        code_files = common.get_files(
            code_org,
            self.args.code_repo,
            self.args.cloud,
            self.args.config_version,
        )

        config_hash = common.get_hash_of_latest_commit(
            config_org, self.args.config_repo, self.args.config_version
        )
        code_hash = common.get_hash_of_latest_commit(
            code_org, self.args.code_repo, self.args.code_version
        )
        testing_ending = f"{config_hash[:7]}-{code_hash[:7]}"

        return deploy(self.args, code_files, config_files, testing_ending)

    def _config(self):
        return setup(self.args)
