import os
import subprocess
import traceback
from argparse import Namespace
from time import sleep

from slackify import log
from slackify.constants import (
    CONFIGURATION,
    CREDENTIALS,
    ENV_FILE,
    SERVICE_PATH,
    SLACKIFY_ENTRY,
    TMP_SERVICE_PATH,
    TOKEN_KEYS
)
from slackify.slack import get_presence, set_profile
from slackify.spotify import song_as_str


def __init_service():
    if os.path.exists(SERVICE_PATH):
        log.warn(f"The Slackify service already exists at '{SERVICE_PATH}'")
        log.warn("The service will be overwritten")

    log.info(f"Creating service at '{SERVICE_PATH}'")

    with open(TMP_SERVICE_PATH, "w") as f:
        service = f"""[Unit]
Description=Slackify
After=network.target

[Service]
Environment=SLACKIFY_SERVICE=1
EnvironmentFile={ENV_FILE}
ExecStart=/usr/bin/python3 {SLACKIFY_ENTRY} play
TimeoutStartSec=0
Restart=always
RestartSec=5
User={os.getlogin()}

[Install]
WantedBy=multi-user.target
"""

        f.write(service)

    log.info(f"Moving from '{TMP_SERVICE_PATH}' to '{SERVICE_PATH}'")
    subprocess.run(["sudo", "mv", TMP_SERVICE_PATH, SERVICE_PATH], check=True)

def init():
    __init_service()

    log.info("Reloading systemd...")
    subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)

    log.ok("Reload finished!")

def _get_status() -> str:
    result = subprocess.run(
        ["sudo", "systemctl", "is-active", "slackify.service"],
        capture_output=True,
        check=False
    )

    return result.stdout.strip().decode()

def status():
    if not os.path.exists(SERVICE_PATH):
        log.warn(f"The Slackify service doesn't exist")
        init()

    log.info(f"Checking the service's status")
    log.info(f"The service's status is '{_get_status()}'")

def start():
    if not os.path.exists(SERVICE_PATH):
        log.warn(f"The Slackify service doesn't exist at '{SERVICE_PATH}'")
        init()

    if missing_keys := TOKEN_KEYS - CREDENTIALS.keys():
        log.warn(f"The following keys are not set as environment variables or in the '{ENV_FILE}' file:")
        [log.warn(f"- {key}") for key in missing_keys]
        log.warn("Please set them before continuing")
        return

    log.info(f"Starting the service")
    subprocess.run(["sudo", "systemctl", "start", "slackify.service"], check=True)

    log.ok("Service started!")

def stop():
    if not os.path.exists(SERVICE_PATH):
        log.warn(f"The Slackify service doesn't exist")
        init()

    log.info(f"Stopping the service")
    subprocess.run(["sudo", "systemctl", "stop", "slackify.service"], check=True)

    log.ok("Service stopped!")

def reset():
    if not os.path.exists(SERVICE_PATH):
        log.warn(f"The Slackify service doesn't exist")
        init()

    stop()
    start()

def play(arguments: Namespace):
    if os.getenv("SLACKIFY_SERVICE") != "0":
        if _get_status() == "active":
            log.warn("The Slackify process is running. Stop it before using this command")
            return

    if os.getenv("SLACKIFY_SERVICE") and CONFIGURATION:
        arguments.album = CONFIGURATION.get("album", False)
        arguments.progress = CONFIGURATION.get("progress", False)

    try:
        while True:
            if get_presence().json()["presence"] == "away":
                log.info("Your status is away")
                return

            title = song_as_str(arguments)

            if not title:
                return
        
            log.info(title)

            args = {"profile": {
                "status_text": title,
                "status_emoji": ":musical_note:",
                "status_expiration": 0
            }}

            set_profile(args)

            sleep(2)

    except (Exception, KeyboardInterrupt) as e:
        log.err(f"{type(e).__name__}: {e}")
        traceback.print_exc()

        args = {"profile": {
            "status_text": "",
            "status_emoji": "",
            "status_expiration": 0
        }}

        set_profile(args)
