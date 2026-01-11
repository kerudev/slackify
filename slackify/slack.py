from typing import Any
import requests

from slackify.utils import get_token

SLACK_TOKEN = get_token("SLACK_TOKEN")

SLACK_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Authorization": f"Bearer {SLACK_TOKEN}",
}

API_URL = "https://slack.com/api"


def __url(slug: str) -> str:
    return f"{API_URL}/{slug}"

def get_presence() -> str:
    response = requests.get(
        url=__url("users.getPresence"),
        headers=SLACK_HEADERS,
    )

    content = response.json()

    return content["presence"]

def get_profile() -> dict[str, Any]:
    response = requests.get(
        url=__url("users.profile.get"),
        headers=SLACK_HEADERS,
    )

    content = response.json()

    return content["profile"]

def set_profile(args: dict[str, str]) -> requests.Response:
    return requests.post(
        url=__url("users.profile.set"),
        headers=SLACK_HEADERS,
        json={"profile": args},
    )

def set_photo(cover_url: str) -> requests.Response:
    response = requests.get(cover_url)
    image_bytes = response.content
    content_type = response.headers.get("Content-Type", "image/jpeg")

    headers = {
        "Authorization": SLACK_HEADERS["Authorization"],
    }

    args = {
        "image": ("cover.jpg", image_bytes, content_type)
    }

    return requests.post(
        url=__url("users.setPhoto"),
        headers=headers,
        files=args,
    )
