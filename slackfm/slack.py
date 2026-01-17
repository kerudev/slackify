from typing import Any
import urllib.request
import uuid

from slackfm import log
from slackfm.constants import PREV_PICTURE_FILE
from slackfm.utils import get_token, dispatch

SLACK_TOKEN = get_token("SLACK_TOKEN")

SLACK_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Authorization": f"Bearer {SLACK_TOKEN}",
}

API_URL = "https://slack.com/api"


def __url(slug: str) -> str:
    return f"{API_URL}/{slug}"

def _post(
    url: str,
    json: dict[str, Any],
    headers: dict[str, Any] = SLACK_HEADERS,
    encode_json: bool = True,
) -> str | bytes:
    data = str(json).encode() if encode_json else json

    req = urllib.request.Request(
        url=__url(url),
        headers=headers,
        data=data,
        method="POST",
    )

    return dispatch(req)

def _get(
    url: str,
    headers: dict[str, Any] = SLACK_HEADERS,
    parse_url: bool = True,
) -> str | bytes:
    url = __url(url) if parse_url else url

    req = urllib.request.Request(
        url=url,
        headers=headers,
        method="GET",
    )

    return dispatch(req)

def get_presence() -> str:
    response = _get("users.getPresence")
    return response["presence"]

def get_profile() -> dict[str, Any]:
    response = _get("users.profile.get")
    return response["profile"]

def set_profile(args: dict[str, str]) -> str:
    return _post(
        url="users.profile.set",
        json={"profile": args},
    )

def reset_profile(image_url: str) -> str:
    args = {
        "status_text": "",
        "status_emoji": "",
        "status_expiration": 0,
    }

    log.info("Resetting the profile info")
    set_profile(args)

    if not image_url:
        if not PREV_PICTURE_FILE.exists():
            log.warn("The previous profile picture can't be found")
            exit(1)

        with open(PREV_PICTURE_FILE, "r") as f:
            image_url = f.readline()

    log.info("Resetting the profile picture")
    set_photo(image_url)

def set_photo(image_url: str) -> str:
    response: bytes = _get(image_url, parse_url=False)

    boundary = uuid.uuid4().hex

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="cover.jpg"\r\n'
        f'Content-Type: image/jpeg\r\n\r\n'
    ).encode()

    body += response
    body += f"\r\n--{boundary}--\r\n".encode()

    headers = {
        "Authorization": SLACK_HEADERS["Authorization"],
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    }

    return _post(
        url="users.setPhoto",
        headers=headers,
        json=body,
        encode_json=False,
    )
