from settings import SETTINGS


def check(cloud_checker_fn, config_file_list):
    return cloud_checker_fn(config_file_list)


def gcp(config_file_list):
    pass


def aws(config_file_list):
    pass


def triton(config_file_list):
    pass


def all_(config_file_list):
    for cloud in SETTINGS.SUPPORTED_CLOUDS:
        cloud(config_file_list)
