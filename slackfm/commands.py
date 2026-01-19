import os
import subprocess
import time
import traceback
from argparse import Namespace

from slackfm import log
from slackfm.api import spotify
from slackfm.constants import (
    ENV_FILE,
    PREV_PICTURE_FILE,
    SERVICE_PATH,
    TOKEN_KEYS,
)
from slackfm.utils import get_flags, get_service_status, init_service, read_tokens

# TMP
try:
    from slackfm.browser import slack
except ImportError:
    from slackfm.api import slack


def __check_service_exists():
    if not SERVICE_PATH.exists():
        log.warn(f"The SlackFM service doesn't exist at '{SERVICE_PATH}'")
        init()


def init():
    init_service()

    log.info("Reloading systemd...")
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)

    log.ok("Reload finished!")


def status():
    __check_service_exists()

    log.info("Checking the service's status")
    log.info(f"The service's status is '{get_service_status()}'")


def start():
    __check_service_exists()

    if missing_keys := TOKEN_KEYS - read_tokens().keys():
        log.warn("The following keys were not set:")
        [log.warn(f"- {key}") for key in missing_keys]
        log.warn(f"Please set them as env vars or in the '{ENV_FILE}' file")

        exit(1)

    log.info("Starting the service")
    subprocess.run(["sudo", "systemctl", "start", "slackfm.service"], check=True)

    log.ok("Service started!")


def stop():
    __check_service_exists()

    log.info("Stopping the service")
    subprocess.run(["sudo", "systemctl", "stop", "slackfm.service"], check=True)

    log.ok("Service stopped!")

    slack.reset_profile()


def reset():
    __check_service_exists()

    log.info("Resetting the service")
    subprocess.run(["sudo", "systemctl", "restart", "slackfm.service"], check=True)

    log.ok("Service resetted!")


def play(arguments: Namespace):
    if os.getenv("SLACKFM_SERVICE") != "1" and get_service_status() == "active":
        log.warn("The SlackFM process is running. Stop it before using this command")
        return

    if os.getenv("SLACKFM_SERVICE"):
        flags = get_flags()

        arguments.album = flags.get("album", False)
        arguments.progress = flags.get("progress", False)
        arguments.cover = flags.get("cover", False)

    previous_photo: str = slack.get_profile()["image_512"]

    with open(PREV_PICTURE_FILE, "w") as f:
        f.write(previous_photo)

    # Don't modify previous_photo from this point, as it's used in the except block
    previous_cover_url = previous_photo

    try:
        while True:
            if slack.get_presence() == "away":
                log.info("Your status is away")
                return

            if not (song := spotify.get_song()):
                return

            if not (title := spotify.song_as_str(song, arguments)):
                stop()
                return

            log.info(title)

            args = {
                "status_text": title,
                "status_emoji": ":musical_note:",
                "status_expiration": 0,
            }

            time.sleep(2)
            slack.set_profile(args)

            if not arguments.cover:
                continue

            cover_url = song["item"]["album"]["images"][0]["url"]

            if previous_cover_url == cover_url:
                continue

            previous_cover_url = cover_url
            slack.set_photo(cover_url)

    except (Exception, KeyboardInterrupt) as e:
        log.err(f"{type(e).__name__}: {e}")
        traceback.print_exc()

        slack.reset_profile(previous_photo)
