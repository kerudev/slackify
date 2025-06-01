#!/usr/bin/python3

import os

from slackify import actions, args, log

def main():
    arguments = args.parse()

    if arguments.command == args.Command.PLAY.value:
        actions.play(arguments)
        return

    if os.getuid() != 0:
        log.warn("You may be asked to authenticate as sudo.")

    match arguments.command:
        case args.Command.INIT.value:
            actions.init()

        case args.Command.START.value:
            actions.start()

        case args.Command.STOP.value:
            actions.stop()

        case default:
            log.err(f"There is no function associated to the '{default}' command")

if __name__ == "__main__":
    main()
