import argparse
from datetime import datetime

import common
import reporter.local

from deployer import deploy

# from checker import check
from code_control import setup, TemplatesArgAction

from settings import SETTINGS


class CloudControlException(Exception):
    pass


class ArgumentsParser:
    """
    That class used for subparsers setup, and storing all parsed arguments.
    """

    def __init__(self, args=None):
        self.root_parser = common.root_parser()
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
            "--cloud", choices=["all"] + SETTINGS.SUPPORTED_CLOUDS
        )
        deploy_parser.add_argument(
            "--code-repo",
            help="Name of the repository with terraform infrastructure code. If not specified, defaults to project id.",
            required=True,
        )
        deploy_parser.add_argument(
            "--config-repo",
            help="Name of the repository with terraform variables files",
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
            "--config-repo",
            help="Name of the repository with terraform variables files. If not specified, defaults to project id.",
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


class CloudControl:
    """
    Entry point. Calls specific command passed to cli-app.
    """

    def __init__(self, args):
        self.args = args

        self._setup_logger()
        self._setup_app_metrics()

    def _setup_logger(self):
        self._log = reporter.local.get_logger(
            __name__, self.args.log_file, self.args.debug
        )

    def _setup_app_metrics(self):
        if getattr(self.args, "key_file", None):
            auth = common.GcpAuth(self.args.key_file)
        else:
            auth = common.GcpAuth()

        self._app_metrics = reporter.stackdriver.AppMetrics(
            monitoring_credentials=auth.credentials,
            monitoring_project=self.args.monitoring_namespace,
            metrics_set_list=[],
        )

    def _log_and_send_metrics(self, command, command_result):
        self._log.info("finished " + command + " run")
        self._app_metrics.end_time = datetime.utcnow()

        self._app_metrics.metrics_set_list = [
            {
                "metric_name": "deployment_time",
                "labels": {
                    "result": "success" if command_result else "failure",
                    "command": self.args.command,
                },
                "metric_kind": "gauge",
                "value_type": "double",
                "value": self._app_metrics.app_runtime.total_seconds(),
            },
            {
                "metric_name": "deployments_rate",
                "labels": {
                    "result": "success" if command_result else "failure",
                    "command": self.args.command,
                },
                "metric_kind": "cumulative",
                "value_type": "int64",
                "value": 1,
                "unit": "h",
            },
        ]
        self._app_metrics.send_metrics()

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

        result = False
        try:
            result = command()
        finally:
            self._log_and_send_metrics(self.args.command, result)

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
            config_org, self.args.project_id, self.args.config_version
        )
        code_hash = common.get_hash_of_latest_commit(
            code_org, self.args.project_id, self.args.config_version
        )
        testing_ending = f"{config_hash[:7]}-{code_hash[:7]}"

        return deploy(self.args, code_files, config_files, testing_ending)

    def _config(self):
        return setup(self.args)
