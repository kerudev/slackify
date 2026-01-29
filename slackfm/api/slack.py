import json
import urllib.request
import uuid
from typing import Any

from slackfm import log
from slackfm.constants import PREVIOUS_FILE
from slackfm.utils import dispatch, get_token

SLACK_TOKEN = get_token("SLACK_TOKEN")

SLACK_HEADERS = {
    "Content-Type": "application/json; charset=utf-8",
    "Authorization": f"Bearer {SLACK_TOKEN}",
}

SLACK_API_URL = "https://slack.com/api"


def __url(slug: str) -> str:
    return f"{SLACK_API_URL}/{slug}"


def _post(
    slug: str,
    headers: dict[str, Any] = SLACK_HEADERS,
    *,
    data: dict[str, Any] | bytes,
) -> dict[str, Any]:
    """
    Make a `GET` request.

    Parameters
    ----------
    slug: str
        The endpoint which will be requested.
    headers: dict[str, Any] = SLACK_HEADERS
        The request's headers.
    data: dict[str, Any] | bytes
        The request's body.

    Returns
    -------
    dict[str, Any]
        The response.
    """
    data = str(data).encode() if not isinstance(data, bytes) else data

    req = urllib.request.Request(url=__url(slug), headers=headers, data=data)

    return dispatch(req)


def _get(
    slug: str,
    headers: dict[str, Any] = SLACK_HEADERS,
    *,
    parse_url: bool = True,
) -> str | bytes:
    """
    Make a `GET` request.

    Parameters
    ----------
    slug: str
        The endpoint which will be requested.
    headers: dict[str, Any] = SLACK_HEADERS
        The request's headers.
    parse_url: bool = True
        If `True`, `slug` will be concatenated to `SLACK_API_URL`.
        If `False`, `slug` is expected to be a full URL.

    Returns
    -------
    str | bytes
        The response.
    """
    url = __url(slug) if parse_url else slug

    req = urllib.request.Request(url=url, headers=headers)

    return dispatch(req)


def get_presence() -> str:
    """
    Obtain the presence of a user.

    Docs: https://docs.slack.dev/reference/methods/users.getPresence/
    Rate limit: `Tier 3: 50+ per minute`

    Returns
    -------
    str
        "active" or "away"
    """
    response = _get("users.getPresence")
    return response["presence"]


def get_profile() -> dict[str, Any]:
    """
    Obtain the user's profile information.

    Docs: https://docs.slack.dev/reference/methods/users.profile.get/
    Rate limit: `Tier 4: 100+ per minute`

    Returns
    -------
    dict[str, Any]
        A dictionary with the following keys: `status_text`, `status_emoji`,
        `status_expiration` and `image_512`.
    """
    response = _get("users.profile.get")
    profile = response["profile"]

    return {
        "status_text": profile["status_text"],
        "status_emoji": profile["status_emoji"],
        "status_expiration": 0,
        "image_512": profile["image_512"],
    }


def set_profile(args: dict[str, str]) -> dict[str, Any]:
    """
    Set the user's profile information.

    Docs: https://docs.slack.dev/reference/methods/users.profile.set
    Rate limit: `Tier 3: 50+ per minute`

    Returns
    -------
    dict[str, Any]
        The response.
    """
    return _post("users.profile.set", data={"profile": args})


def reset_profile() -> None:
    """
    Call `set_profile` and `set_photo`.

    The `PREVIOUS_FILE` is expected to exist. If it doesn't, the program will
    exit with an error code.
    """
    if not PREVIOUS_FILE.exists():
        log.warn("The previous profile file can't be found")
        exit(1)

    with open(PREVIOUS_FILE, "r") as f:
        previous = json.load(f)

    profile_picture = previous.pop("image_512")

    log.info("Resetting the profile info")
    set_profile(previous)

    log.info("Resetting the profile picture")
    set_photo(profile_picture)


def set_photo(image_url: str) -> dict[str, Any]:
    """
    Set the user's profile picture.

    Docs: https://docs.slack.dev/reference/methods/users.setPhoto
    Rate limit: `Tier 2: 20+ per minute`

    Returns
    -------
    dict[str, Any]
        The response.
    """
    response: bytes = _get(image_url, parse_url=False)

    boundary = uuid.uuid4().hex

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="cover.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode()

    body += response
    body += f"\r\n--{boundary}--\r\n".encode()

    headers = {
        "Authorization": SLACK_HEADERS["Authorization"],
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    }

    return _post("users.setPhoto", headers, data=body)
