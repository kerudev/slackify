import datetime
import requests
import os

SLACK_URL = "https://slack.com/api"
SLACK_TOKEN = os.getenv("SLACK_TOKEN")

def __url(slug: str) -> str:
    return f"{SLACK_URL}/{slug}"

def __headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {SLACK_TOKEN}",
    }

def get_presence():
    return requests.get(
        url=__url("users.getPresence"),
        headers=__headers()
    )

def set_profile(args: dict[str, str]) -> requests.Response:
    return requests.post(
        url=__url("users.profile.set"),
        headers=__headers(),
        json=args,
    )