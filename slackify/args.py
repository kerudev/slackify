import argparse
from enum import StrEnum


class Command(StrEnum):
    PLAY = "play"
    INIT = "init"
    START = "start"
    STOP = "stop"

def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="command", required=True)
    
    play = subparsers.add_parser(Command.PLAY.value, help="Initializes Slackify in the current shell session")

    play_group = play.add_mutually_exclusive_group(required=False)
    play_group.add_argument("--album", action="store_true", help="show the album's title")
    play_group.add_argument("--progress", action="store_true", help="show the song's progress (time until it finishes)")

    subparsers.add_parser(Command.INIT.value, help="Creates the Slackify system service (systemd)")
    subparsers.add_parser(Command.START.value, help="Starts Slackify as a system service (systemd)")
    subparsers.add_parser(Command.STOP.value, help="Stops Slackify as a system service (systemd)")

    return parser.parse_args()
