import logging
from sys import stdout


def get_logger(module_name: str, log_file: str, debug: bool = False):
    logger = logging.getLogger(module_name)
    logger.setLevel(logging.INFO)
    file_stream = logging.FileHandler(log_file)

    fmt = logging.Formatter('%(asctime)s [%(application)s] [%(threadName)s] '
                            '[%(name)s] %(levelname)s: %(message)s')
    file_stream.setFormatter(fmt)
    logger.addHandler(file_stream)
    if debug:
        debug_stream = logging.StreamHandler(stdout)
        debug_stream.setFormatter(fmt)
        logger.addHandler(debug_stream)
        logger.setLevel(logging.DEBUG)
