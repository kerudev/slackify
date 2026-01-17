import gzip
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request
import zlib

import urllib

from slackfm import log
from slackfm.constants import CONF_FILE, ENV_FILE, SERVICE_PATH, TMP_SERVICE_PATH

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

def read_response(res: http.client.HTTPResponse) -> str | bytes:
    raw = res.read() or b"{}"
    headers = res.headers or {}

    if "image" in headers.get("Content-Type", ""):
        return raw

    encoding = headers.get("Content-Encoding")

    if encoding == "gzip":
        body = gzip.decompress(raw)
    elif encoding == "deflate":
        body = zlib.decompress(raw)
    else:
        body = raw.decode()

    return json.loads(body)

def dispatch(req: urllib.request.Request) -> str | bytes:
    try:
        with urllib.request.urlopen(req) as res:
            return read_response(res)

    except urllib.error.HTTPError as e:
        return read_response(e)

def init_service():
    if SERVICE_PATH.exists():
        log.warn(f"The SlackFM service already exists at '{SERVICE_PATH}'")
        log.warn("The service will be overwritten")

    log.info(f"Creating service at '{SERVICE_PATH}'")

    slackfm = Path(sys.argv[0]).resolve()

    with open(TMP_SERVICE_PATH, "w") as f:
        f.write(f"""[Unit]
Description=SlackFM
After=network.target

[Service]
Environment=SLACKFM_SERVICE=1
EnvironmentFile={ENV_FILE}
ExecStart={slackfm} play
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
        ["systemctl", "is-active", "slackfm.service"],
        capture_output=True,
        check=False
    )

    return result.stdout.strip().decode()