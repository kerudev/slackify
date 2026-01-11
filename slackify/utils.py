import os
from pathlib import Path
import subprocess
import sys

from slackify import log
from slackify.constants import CONF_FILE, ENV_FILE, SERVICE_PATH, TMP_SERVICE_PATH

def file_to_dict(filename: Path) -> list[str]:
    if not filename.exists():
        log.info(f"Creating file at '{filename}'")
        subprocess.run(["touch", filename], check=True)

    with open(filename, "r") as f:
        return [line.strip().split("=") for line in f]

def read_tokens() -> dict[str, str]:
    return {
        pair[0].upper(): pair[1]
        for pair in file_to_dict(ENV_FILE)
    }

def get_flags() -> dict[str, str]:
    return {
        pair[0].lower(): pair[1].lower()
        in ("true", "1")
        for pair in file_to_dict(CONF_FILE)
    }

def get_token(key: str) -> str:
    return os.getenv(key, read_tokens().get(key))

def init_service():
    if SERVICE_PATH.exists():
        log.warn(f"The Slackify service already exists at '{SERVICE_PATH}'")
        log.warn("The service will be overwritten")

    log.info(f"Creating service at '{SERVICE_PATH}'")

    slackify = Path(sys.argv[0]).resolve()

    with open(TMP_SERVICE_PATH, "w") as f:
        f.write(f"""[Unit]
Description=Slackify
After=network.target

[Service]
Environment=SLACKIFY_SERVICE=1
EnvironmentFile={ENV_FILE}
ExecStart={slackify} play
TimeoutStartSec=0
Restart=always
RestartSec=5
User={os.getlogin()}

[Install]
WantedBy=multi-user.target
""")

    log.info(f"Moving '{TMP_SERVICE_PATH}' to '{SERVICE_PATH}'")
    subprocess.run(["sudo", "mv", TMP_SERVICE_PATH, SERVICE_PATH], check=True)

def get_service_status() -> str:
    result = subprocess.run(
        ["systemctl", "is-active", "slackify.service"],
        capture_output=True,
        check=False
    )

    return result.stdout.strip().decode()