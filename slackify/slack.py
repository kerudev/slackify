import requests

from slackify.constants import CREDENTIALS, KEY_SLACK_TOKEN, SLACK_URL

SLACK_TOKEN = CREDENTIALS[KEY_SLACK_TOKEN]

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

def get_profile() -> requests.Response:
    return requests.get(
        url=__url("users.profile.get"),
        headers=__headers(),
    )

def set_profile(args: dict[str, str]) -> requests.Response:
    return requests.post(
        url=__url("users.profile.set"),
        headers=__headers(),
        json=args,
    )

def set_photo(cover_url: str) -> requests.Response:
    response = requests.get(cover_url)
    image_bytes = response.content
    content_type = response.headers.get("Content-Type", "image/jpeg")

    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
    }

    args = {
        "image": ("cover.jpg", image_bytes, content_type)
    }

    response = requests.post(
        url=__url("users.setPhoto"),
        headers=headers,
        files=args,
    )

    return response
