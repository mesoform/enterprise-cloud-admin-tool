import argparse
from datetime import datetime

import builder
import reporter.stackdriver
import reporter.local

from settings import Settings

settings = Settings()


def get_parsed_args():
    root_parser = builder.arg_parser()
    root_parser.description = \
        'cloud_control is an application for managing cloud infrastructure in' \
        ' the enterprise. It interfaces with other known tooling like' \
        ' Terraform, GitHub and Jira. It does this rather than try to create' \
        ' something new so as to maintain clear delegation of duties but also' \
        ' allowing cross-functional working by keeping different functions' \
        ' separated in reusable modules'

    def add_deploy_parser(parser):
        d_parser = parser.add_parser('deploy',
                                     help='deploy configuration to the cloud')
        d_parser.formatter_class = argparse.RawTextHelpFormatter
        d_parser.add_argument(
            '--cloud', choices=['all'] + settings.SUPPORTED_CLOUDS)
        return d_parser

    def add_config_parser(parser):
        c_parser = parser.add_parser(
            'config',
            help='Administer cloud configuration on respective repository')
        c_parser.formatter_class = argparse.RawTextHelpFormatter
        c_parser.add_argument('--github')
        c_parser.add_argument(
            'c_action', choices=('create', 'delete', 'update'))
        return c_parser

    mgmt_parser = root_parser.add_subparsers(
        help='manage infrastructure deployment or infrastructure'
             ' configuration',
        dest='command')

    add_deploy_parser(mgmt_parser)
    add_config_parser(mgmt_parser)

    return root_parser.parse_args()


def perform_commands():
    parsed_args = get_parsed_args()
    if getattr(parsed_args, "key_file", None):
        auth = builder.GcpAuth(parsed_args.key_file)
    else:
        auth = builder.GcpAuth()

    __app_metrics = reporter.stackdriver.AppMetrics(
        monitoring_credentials=auth.credentials,
        monitoring_project=parsed_args.monitoring_namespace
    )
    __log = reporter.local.get_logger(__name__, parsed_args.log_file, parsed_args.debug)

    try:
        if parsed_args.command == 'deploy':
            __log.info('Starting deployment')
            if parsed_args.cloud == 'all':
                parsed_args.cloud = 'all_'
            from deployer import deploy
            from checker import check
            config_org = builder.get_org(parsed_args, parsed_args.config_org)
            code_org = builder.get_org(parsed_args, parsed_args.code_org)
            config_files = builder.get_files(config_org, parsed_args.project_id,
                                             parsed_args.cloud, parsed_args.config_version)
            # code repo should contain any lists or maps that define
            # security policies
            # and operating requirements. The code repo should be public.
            code_files = builder.get_files(code_org, parsed_args.project_id,
                                           parsed_args.cloud, parsed_args.config_version)
            check(parsed_args.cloud, config_files)
            deploy(parsed_args, code_files, config_files)
        elif parsed_args.command == 'config':
            from code_control import setup
            setup(parsed_args)

    finally:
        __log.info('finished ' + parsed_args.command + ' run')
        __app_metrics.end_time = datetime.utcnow()
        __app_metrics.send_metrics()
