#!/usr/bin/env python3

from cloud_control import ArgumentsParser, CloudControl


def main():
    parser = ArgumentsParser()
    cloud_control = CloudControl(parser.args)
    cloud_control.perform_command()


if __name__ == "__main__":
    main()
