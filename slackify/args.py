import argparse
from enum import StrEnum


class Command(StrEnum):
    PLAY = "play"
    INIT = "init"
    STATUS = "status"
    START = "start"
    STOP = "stop"
    RESET = "reset"

def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="command", required=True)
    
    play = subparsers.add_parser(Command.PLAY.value, help="Initializes Slackify in the current shell session")

    play_group = play.add_mutually_exclusive_group(required=False)
    play_group.add_argument("--album", action="store_true", help="Displays the song's album title (if it's not a single)")
    play_group.add_argument("--progress", action="store_true", help="Show the song's progress (time until it finishes)")
    play_group.add_argument("--cover", action="store_true", help="Temporarily sets your profile picture to the song's cover")

    subparsers.add_parser(Command.INIT.value, help="Creates the Slackify system service (systemd)")
    subparsers.add_parser(Command.STATUS.value, help="Displays the status of the Slackify service (systemd)")
    subparsers.add_parser(Command.START.value, help="Starts Slackify as a system service (systemd)")
    subparsers.add_parser(Command.STOP.value, help="Stops Slackify as a system service (systemd)")
    subparsers.add_parser(Command.RESET.value, help="Stop the Slackify service to start it again (systemd)")

    return parser.parse_args()
