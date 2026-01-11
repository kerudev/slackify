import os
import subprocess
import sys
import traceback
from argparse import Namespace
import time

from pathlib import Path

from slackify import log, slack, spotify
from slackify.constants import (
    ENV_FILE,
    PREV_PICTURE_FILE,
    SERVICE_PATH,
    TOKEN_KEYS,
)
from slackify.utils import get_flags, get_service_status, init_service, read_tokens

def __check_service_exists():
    if not SERVICE_PATH.exists():
        log.warn(f"The Slackify service doesn't exist at '{SERVICE_PATH}'")
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
        log.warn(f"The following keys neither set as env vars nor in the '{ENV_FILE}' file:")
        [log.warn(f"- {key}") for key in missing_keys]
        log.warn("Please set them before continuing")

        exit(1)

    log.info("Starting the service")
    subprocess.run(["sudo", "systemctl", "start", "slackify.service"], check=True)

    log.ok("Service started!")

def stop():
    __check_service_exists()

    log.info("Stopping the service")
    subprocess.run(["sudo", "systemctl", "stop", "slackify.service"], check=True)

    log.ok("Service stopped!")

    args = {
        "status_text": "",
        "status_emoji": "",
        "status_expiration": 0,
    }

    log.info("Resetting the profile info")
    slack.set_profile(args)

    if not PREV_PICTURE_FILE.exists():
        log.warn("The previous profile picture can't be found")
        exit(1)

    log.info("Resetting the profile picture")

    with open(PREV_PICTURE_FILE, "r") as f:
        slack.set_photo(f.readline())

def reset():
    __check_service_exists()

    log.info("Resetting the service")
    subprocess.run(["sudo", "systemctl", "restart", "slackify.service"], check=True)

    log.ok("Service resetted!")

def play(arguments: Namespace):
    if os.getenv("SLACKIFY_SERVICE") != "1" and get_service_status() == "active":
        log.warn("The Slackify process is running. Stop it before using this command")
        return

    flags = get_flags()

    if os.getenv("SLACKIFY_SERVICE") and flags:
        arguments.album = flags.get("album", False)
        arguments.progress = flags.get("progress", False)
        arguments.cover = flags.get("cover", False)

    previous_photo = slack.get_profile()["image_512"]

    with open(PREV_PICTURE_FILE, "w") as f:
        f.write(previous_photo)

    # Don't modify previous_photo from this point, as it's used in the except block 
    previous_cover_url = previous_photo

    try:
        while True:
            if slack.get_presence() == "away":
                log.info("Your status is away")
                return

            response = spotify.get_song()

            if not response.content:
                return

            song = response.json()

            if not (title := spotify.song_as_str(song, arguments)):
                stop()
                return

            log.info(title)

            args = {
                "status_text": title,
                "status_emoji": ":musical_note:",
                "status_expiration": 0
            }

            slack.set_profile(args)

            if not arguments.cover:
                continue

            cover_url = song["item"]["album"]["images"][0]["url"]

            if previous_cover_url == cover_url:
                continue

            previous_cover_url = cover_url
            slack.set_photo(cover_url)

            time.sleep(2)

    except (Exception, KeyboardInterrupt) as e:
        log.err(f"{type(e).__name__}: {e}")
        traceback.print_exc()

        args = {
            "status_text": "",
            "status_emoji": "",
            "status_expiration": 0,
        }

        log.info("Resetting the profile info")
        slack.set_profile(args)

        log.info("Resetting the profile picture")
        slack.set_photo(previous_photo)
