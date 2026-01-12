from typing import Any
import urllib.request

from slackify import log
from slackify.constants import LIB_HEADERS, PREV_PICTURE_FILE
from slackify.utils import get_token, dispatch

SLACK_TOKEN = get_token("SLACK_TOKEN")

SLACK_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Authorization": f"Bearer {SLACK_TOKEN}",
}

API_URL = "https://slack.com/api"


def __url(slug: str) -> str:
    return f"{API_URL}/{slug}"

def __post(url: str, json: dict[str, Any], headers: dict[str, Any] = SLACK_HEADERS) -> str:
    headers = {**LIB_HEADERS, **headers}

    req = urllib.request.Request(
        url=__url(url),
        headers=headers,
        data=str(json).encode('utf-8'),
        method="POST",
    )

    return dispatch(req)

def __get(url: str, headers: dict[str, Any] = SLACK_HEADERS) -> str:
    headers = {**LIB_HEADERS, **headers}

    req = urllib.request.Request(
        url=__url(url),
        headers=headers,
        method="GET",
    )

    return dispatch(req)

def get_presence() -> str:
    response = __get("users.getPresence")
    return response["presence"]

def get_profile() -> dict[str, Any]:
    response = __get("users.profile.get")
    return response["profile"]

def set_profile(args: dict[str, str]) -> str:
    return __post(
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
    response = __get(image_url)
    image_bytes = response.content
    content_type = response.headers.get("Content-Type", "image/jpeg")

    headers = {
        "Authorization": SLACK_HEADERS["Authorization"],
    }

    args = {
        "image": ("cover.jpg", image_bytes, content_type)
    }

    return __post(
        url="users.setPhoto",
        headers=headers,
        files=args,
    )
