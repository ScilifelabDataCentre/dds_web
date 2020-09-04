"Command-line interface."

import argparse
import getpass
import sys

import flask

import code_dds.app
import code_dds.user

from code_dds import constants
from code_dds import utils


def get_parser():
    "Get the parser for the command line interface."
    p = argparse.ArgumentParser(prog="cli.py",
                                usage="python %(prog)s [options]",
                                description="code_dds command line interface")
    p.add_argument("-d", "--debug", action="store_true",
                   help="Debug logging output.")
    x0 = p.add_mutually_exclusive_group()
    x0.add_argument("-A", "--create_admin", action="store_true",
                    help="Create an admin user.")
    x0.add_argument("-U", "--create_user", action="store_true",
                    help="Create a user.")
    return p


def execute(pargs):
    "Execute the command."
    if pargs.debug:
        flask.current_app.config["DEBUG"] = True
        flask.current_app.config["LOGFORMAT"] = "%(levelname)-10s %(message)s"
    if pargs.create_admin:
        with code_dds.user.UserSaver() as saver:
            saver.set_username(input("username > "))
            saver.set_email(input("email > "))
            saver.set_password(getpass.getpass("password > "))
            saver.set_role(constants.ADMIN)
            saver.set_status(constants.ENABLED)
            saver["apikey"] = None
    elif pargs.create_user:
        with code_dds.user.UserSaver() as saver:
            saver.set_username(input("username > "))
            saver.set_email(input("email > "))
            saver.set_password(getpass.getpass("password > "))
            saver.set_role(constants.USER)
            saver.set_status(constants.ENABLED)
            saver["apikey"] = None


def main():
    "Entry point for command line interface."
    parser = get_parser()
    pargs = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_usage()
    with code_dds.app.app.app_context():
        flask.g.db = utils.get_db()
        execute(pargs)


if __name__ == "__main__":
    main()
