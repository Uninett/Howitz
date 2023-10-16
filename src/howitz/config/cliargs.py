from argparse import ArgumentParser
import sys

from .models import ServerConfig, DevServerConfig


def make_argument_parser():
    "Set up the argument parser"
    parser = ArgumentParser("howitz")
    parser.add_argument('--devmode', action="store_true", help='Run in development mode: PORT is set to 9000, LISTEN to "127.0.0.1" and STORAGE to "./howitz.sqlite3"')
    parser.add_argument('-p', '--port', type=int, help="Port to listen on")
    parser.add_argument('-l', '--listen', type=str, help="IP-address to listen on")
    # parser.add_argument('-s', '--storage', type=str, help="Location of sqlite3-file")
    # parser.add_argument('-c', '--config', type=str, default=None, help="Location of config-file, if not in one of the standard locations")
    return parser


def parse_args(parser: ArgumentParser, raw_args=None):
    "Parse and validate args"
    if not raw_args:
        raw_args = sys.argv[1:]
    args = parser.parse_args(raw_args)
    # if args.config:
    #     pass
    if args.devmode:
        devconfig = DevServerConfig()
        if not args.port:
            args.port = devconfig.port
        if not args.listen:
            args.listen = str(devconfig.listen)
    return args
