#!/usr/bin/env python3

import argparse
import logging
import pickle
from os.path import dirname, abspath, join

from salt_lsp.server import salt_server

logging.basicConfig(
    filename="salt-server.log", level=logging.DEBUG, filemode="w"
)


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


def main():
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()

    with open(
        join(dirname(abspath(__file__)), "data", "states.pickle"), "rb"
    ) as states_file:
        states = pickle.load(states_file)
    salt_server.post_init(states)

    if args.tcp:
        salt_server.start_tcp(args.host, args.port)
    else:
        salt_server.start_io()


if __name__ == "__main__":
    main()
