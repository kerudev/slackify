import gzip
import http.client
import json
import os
import subprocess
import sys
import urllib.request
import zlib
from pathlib import Path
from typing import Any

from slackfm import log
from slackfm.constants import CONF_FILE, ENV_FILE, SERVICE_PATH, TMP_SERVICE_PATH


def file_to_dict(path: Path) -> dict[str, str]:
    """
    Parse a file to a dictionary.

    It is expected that `path` refers to a simple text file where each line has
    the following structure: `key=value`.

    Parameters
    ----------
    path: Path
        The file path.

    Returns
    -------
    dict[str, str]
        The parsed content.
    """
    if not path.exists():
        log.info(f"Creating file at '{path}'")
        open(path, "w").close()

    with open(path, "r") as f:
        return dict(line.strip().split("=") for line in f)


def read_tokens() -> dict[str, str]:
    """
    Parse the `ENV_FILE` into a dictionary.

    Returns
    -------
    dict[str, str]
        The file parsed content.
    """
    return {pair[0].upper(): pair[1] for pair in file_to_dict(ENV_FILE).items()}


def get_flags() -> dict[str, str]:
    """
    Parse the `CONF_FILE` into a dictionary.

    Returns
    -------
    dict[str, str]
        The file parsed content.
    """
    return {
        pair[0].lower(): pair[1].lower() in ("true", "1")
        for pair in file_to_dict(CONF_FILE).items()
    }


def get_token(key: str) -> str:
    """
    Read the specified token from `ENV_FILE`.

    Parameters
    ----------
    key: str
        The token name.

    Returns
    -------
    str
        The token value.
    """
    return os.getenv(key, read_tokens().get(key))


def read_response(res: http.client.HTTPResponse) -> str | bytes | dict[str, Any]:
    """
    Take a response and process it.

    Parameters
    ----------
    res: http.client.HTTPResponse
        The response.

    Returns
    -------
    str | bytes | dict[str, Any]
        The processed response.
    """
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


def dispatch(req: urllib.request.Request) -> str | bytes | dict[str, Any]:
    """
    Make a request and return its response.

    Parameters
    ----------
    req: urllib.request.Request
        The request.

    Returns
    -------
    str | bytes | dict[str, Any]
        The response.
    """
    try:
        with urllib.request.urlopen(req) as res:
            return read_response(res)

    except urllib.error.HTTPError as e:
        return read_response(e)


def init_service() -> None:
    """Create a service file for systemctl."""
    if SERVICE_PATH.exists():
        log.warn(f"The SlackFM service already exists at '{SERVICE_PATH}'")
        log.warn("The service will be overwritten")

    log.info(f"Creating service at '{SERVICE_PATH}'")

    slackfm = Path(sys.argv[0]).resolve()

    with open(TMP_SERVICE_PATH, "w") as f:
        f.write(
            f"""[Unit]
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
"""
        )

    log.info(f"Moving '{TMP_SERVICE_PATH}' to '{SERVICE_PATH}'")
    subprocess.run(["sudo", "mv", TMP_SERVICE_PATH, SERVICE_PATH], check=True)


def get_service_status() -> str:
    """
    Get the service status.

    The returned value will be one of the listed in
    `https://www.man7.org/linux/man-pages/man1/systemctl.1.html`

    Returns
    -------
    str
        "active", "inactive", "failed", "activating", "deactivating",
        "maintenance", "reloading" or "refreshing"
    """
    result = subprocess.run(
        ["systemctl", "is-active", "slackfm.service"],
        capture_output=True,
        check=False,
    )

    return result.stdout.strip().decode()
