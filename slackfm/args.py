import argparse
from enum import Enum
import os

from slackfm import log, commands


class Command(str, Enum):
    PLAY = "play"
    INIT = "init"
    STATUS = "status"
    START = "start"
    STOP = "stop"
    RESET = "reset"

def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="command", required=True)

    play = subparsers.add_parser(Command.PLAY.value, help="Initializes SlackFM in the current shell session")
    play.add_argument("--album", action="store_true", help="Displays the song's album title (if it's not a single)")
    play.add_argument("--progress", action="store_true", help="Show the song's progress (time until it finishes)")
    play.add_argument("--cover", action="store_true", help="Temporarily sets your profile picture to the song's cover")

    if os.name != "nt":
        subparsers.add_parser(Command.INIT.value,   help="(systemctl) Creates the SlackFM system service")
        subparsers.add_parser(Command.STATUS.value, help="(systemctl) Displays the status of the SlackFM service")
        subparsers.add_parser(Command.START.value,  help="(systemctl) Starts SlackFM as a system service")
        subparsers.add_parser(Command.STOP.value,   help="(systemctl) Stops SlackFM as a system service")
        subparsers.add_parser(Command.RESET.value,  help="(systemctl) Stop the SlackFM service to start it again")

    return parser.parse_args()

def main():
    arguments = parse()

    if os.getuid() != 0:
        log.warn("You may be asked to authenticate as sudo.")

    if not (func := getattr(commands, arguments.command, None)):
        log.err(f"There is no function associated to the '{arguments.command}' command")
        exit(1)

    if func.__name__ == "play":
        func(arguments)
        exit(0)

    func()
