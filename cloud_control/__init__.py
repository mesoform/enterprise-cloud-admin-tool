import argparse
from datetime import datetime

import common
import reporter.local

from deployer import deploy
from checker import check
from code_control import setup

from settings import Settings

SETTINGS = Settings()


class CloudControl:
    """
    Entry point, here we parse all passed cli arguments and
    call specific command (i.e. deploy or config).
    """

    def __init__(self):
        self.root_parser = common.root_parser()
        self.management_parser = self.root_parser.add_subparsers(
            help="manage infrastructure deployment or infrastructure"
            " configuration",
            dest="command",
        )
        self._setup_deploy_parser()
        self._setup_config_parser()

        self.args = self.root_parser.parse_args()

        self._setup_app_metrics()
        self._setup_logger()

        self._perform_command()

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

    def _setup_config_parser(self):
        """
        Setup specific to config command arguments
        """
        config_parser = self.management_parser.add_parser(
            "config",
            help="Administer cloud configuration on respective repository",
        )
        config_parser.formatter_class = argparse.RawTextHelpFormatter
        config_parser.add_argument("--github")
        config_parser.add_argument(
            "c_action", choices=("create", "delete", "update")
        )

    def _setup_logger(self):
        self.__log = reporter.local.get_logger(
            __name__, self.args.log_file, self.args.debug
        )

    def _setup_app_metrics(self):
        if getattr(self.args, "key_file", None):
            auth = common.GcpAuth(self.args.key_file)
        else:
            auth = common.GcpAuth()

        self.__app_metrics = reporter.stackdriver.AppMetrics(
            monitoring_credentials=auth.credentials,
            monitoring_project=self.args.monitoring_namespace,
        )

    def _perform_command(self):
        """
        Checks that passed command implemented in entry point class,
        runs it, logs that command was runned and sends metrics.
        """
        if not hasattr(self, self.args.command):
            print("Unrecognized command")
            self.root_parser.print_help()
            exit(1)

        try:
            getattr(self, self.args.command)()
        finally:
            self.__log.info("finished " + self.args.command + " run")
            self.__app_metrics.end_time = datetime.utcnow()
            self.__app_metrics.send_metrics()

    def deploy(self):
        self.__log.info("Starting deployment")
        if self.args.cloud == "all":
            self.args.cloud = "all_"
        config_org = common.get_org(self.args, self.args.config_org)
        code_org = common.get_org(self.args, self.args.code_org)
        config_files = common.get_files(
            config_org,
            self.args.project_id,
            self.args.cloud,
            self.args.config_version,
        )
        # code repo should contain any lists or maps that define
        # security policies
        # and operating requirements. The code repo should be public.
        code_files = common.get_files(
            code_org,
            self.args.project_id,
            self.args.cloud,
            self.args.config_version,
        )
        check(self.args.cloud, config_files)
        deploy(self.args, code_files, config_files)

    def config(self):
        setup(self.args)
