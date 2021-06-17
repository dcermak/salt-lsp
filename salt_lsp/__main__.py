import argparse
import logging
import pickle
from os.path import dirname, abspath, join
from typing import Dict

from salt_lsp.server import SaltServer, setup_salt_server_capabilities
from salt_lsp.base_types import StateNameCompletion


LOG_LEVEL_DICT: Dict[str, int] = {
    "critical": logging.CRITICAL,
    "fatal": logging.FATAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "warn": logging.WARN,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


def loglevel_from_str(level: str) -> int:
    if level.lower() not in LOG_LEVEL_DICT:
        return logging.DEBUG
    return LOG_LEVEL_DICT[level.lower()]


def add_arguments(parser):
    parser.description = "salt state server"

    parser.add_argument(
        "--tcp", action="store_true", help="Use TCP server instead of stdio"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind to this address"
    )
    parser.add_argument(
        "--port", type=int, default=2087, help="Bind to this port"
    )
    parser.add_argument(
        "--stop-after-init",
        action="store_true",
        help="initialize the server, but don't launch it "
        "(useful for debugging/testing purposes)",
    )
    parser.add_argument(
        "--log-level",
        choices=list(LOG_LEVEL_DICT.keys())
        + list(map(lambda level: level.upper(), LOG_LEVEL_DICT.keys())),
        default=["debug"],
        nargs=1,
        help="Logging verbosity",
    )


def main():
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()

    log_level = loglevel_from_str(args.log_level[0])
    logging.basicConfig(
        filename="salt-server.log",
        level=log_level,
        filemode="w",
    )

    with open(
        join(dirname(abspath(__file__)), "data", "states.pickle"), "rb"
    ) as states_file:
        states: Dict[str, StateNameCompletion] = pickle.load(states_file)

    salt_server = SaltServer()
    setup_salt_server_capabilities(salt_server)
    salt_server.post_init(states, log_level)

    if args.stop_after_init:
        return

    if args.tcp:
        salt_server.start_tcp(args.host, args.port)
    else:
        salt_server.start_io()


if __name__ == "__main__":
    main()
