import builder
import argparse
import reporter.stackdriver
import reporter.local
from datetime import datetime

DEFAULT_LOG_FILE = '/var/log/enterprise_cloud_admin.log'


def get_settings():
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
            '--cloud', choices=['all'] + builder.SUPPORTED_CLOUDS)
        d_parser.add_argument('--key-file',
                              help='path to the file containing the private '
                                   'key used for authentication on CSP',
                              type=argparse.FileType('r'))
        d_parser.add_argument('--log-file',
                              help='path to file, if different from default',
                              default=DEFAULT_LOG_FILE)
        d_parser.add_argument('--debug',
                              help='output debug information to help troubleshoot issues',
                              default=False)
        d_parser.add_argument('--monitoring-namespace',
                              help='CSP specific location where monitoring data is aggregated. For'
                                   'example, a GCP project')
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


def main():
    settings = get_settings()
    if settings.key_file:
        auth = builder.GcpAuth(settings.key_file)
    else:
        auth = builder.GcpAuth()

    __app_metrics = reporter.stackdriver.AppMetrics(
        monitoring_credentials=auth.credentials,
        monitoring_project=settings.monitoring_namespace
    )
    __log = reporter.local.get_logger(__name__, settings.log_file, settings.debug)

    try:
        if settings.command == 'deploy':
            __log.info('Starting deployment')
            if settings.cloud == 'all':
                settings.cloud = 'all_'
            from deployer import deploy
            from checker import check
            config_org = builder.get_org(settings, settings.config_org)
            code_org = builder.get_org(settings, settings.code_org)
            config_files = builder.get_files(config_org, settings.project_id,
                                             settings.cloud, settings.version)
            # code repo should contain any lists or maps that define
            # security policies
            # and operating requirements. The code repo should be public.
            code_files = builder.get_files(code_org, settings.project_id,
                                           settings.cloud, settings.version)
            check(settings.cloud, config_files)
            deploy(settings, code_files, config_files)
        elif settings.command == 'config':
            # import code_control

            # set up monitoring

            # deploy standard monitoring configuration
            pass
    finally:
        __log.info('finished ' + settings.command + ' run')
        __app_metrics.end_time = datetime.utcnow()
        __app_metrics.send_metrics()
