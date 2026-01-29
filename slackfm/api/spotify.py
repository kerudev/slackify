import base64
import http.server
import json
import os
import random
import socketserver
import string
import urllib.parse
import urllib.request
import webbrowser
from argparse import Namespace
from typing import Any

from slackfm import log
from slackfm.constants import CONFIG_PATH
from slackfm.utils import dispatch, get_token

SPOTIFY_TOKEN_ENDPOINT = "https://accounts.spotify.com/api/token"

SPOTIFY_TOKEN_PATH = CONFIG_PATH / "tokens"
SPOTIFY_TOKEN_FILE = SPOTIFY_TOKEN_PATH / "spotify_token.json"
os.makedirs(SPOTIFY_TOKEN_PATH, exist_ok=True)

SPOTIFY_CLIENT_ID = get_token("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = get_token("SPOTIFY_CLIENT_SECRET")

SPOTIFY_ENCODED_AUTH = base64.b64encode(
    f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
).decode()

SPOTIFY_TOKEN_HEADERS = {
    "Authorization": f"Basic {SPOTIFY_ENCODED_AUTH}",
    "Content-Type": "application/x-www-form-urlencoded",
}

# Used to request the token for the first time (or if it isn't stored in a file)
PORT = 8888
REDIRECT_URI = f"http://127.0.0.1:{PORT}/callback"


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self):
        super().__init__(("", PORT), SpotifyTokenHandler)
        self.token_response = None


class SpotifyTokenHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(302)
        self.send_header("Location", "https://open.spotify.com/")
        self.end_headers()

        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        code = query.get("code", [""])[0]

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }

        response = _post(SPOTIFY_TOKEN_ENDPOINT, SPOTIFY_TOKEN_HEADERS, data=data)

        self.server.token_response = response


def __calc_time(millis: int) -> str:
    total_secs = millis // 1000

    mins = total_secs // 60
    secs = total_secs % 60

    return f"{mins}:{secs:02d}"


def _get(url: str, headers: dict[str, Any]) -> str | dict[str, str]:
    """
    Make a `GET` request.

    Parameters
    ----------
    url: str
        The URL which will be requested.
    headers: dict[str, Any]
        The request's headers.

    Returns
    -------
    str | dict[str, str]
        The response.
    """
    req = urllib.request.Request(url=url, headers=headers)

    return dispatch(req)


def _post(url: str, headers: dict[str, Any], *, data: dict[str, Any]) -> str:
    """
    Make a `POST` request.

    Parameters
    ----------
    url: str
        The URL which will be requested.
    headers: dict[str, Any]
        The request's headers.
    data: dict[str, Any] | bytes
        The request's body.

    Returns
    -------
    str
        The response.
    """
    data = urllib.parse.urlencode(data).encode()

    req = urllib.request.Request(url=url, headers=headers, data=data)

    return dispatch(req)


def read_token() -> dict[str, str]:
    """
    Read the token from `SPOTIFY_TOKEN_FILE`.

    If `SPOTIFY_TOKEN_FILE` doesn't exist, a new token is requested.

    Returns
    -------
    dict[str, str]
        The token data.
    """
    if SPOTIFY_TOKEN_FILE.exists():
        with open(SPOTIFY_TOKEN_FILE, "r") as f:
            return json.load(f)

    token = request_token()

    with open(SPOTIFY_TOKEN_FILE, "w") as f:
        json.dump(token, f)

    return token


def request_token() -> dict[str, str]:
    """
    Request a new token.

    Returns
    -------
    dict[str, str]
        The token data.
    """
    chars = string.ascii_uppercase + string.digits
    state = "".join(random.choice(chars) for _ in range(16))

    params = {
        "response_type": "code",
        "client_id": SPOTIFY_CLIENT_ID,
        "scope": "user-read-currently-playing",
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }

    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)

    with ReusableTCPServer() as httpd:
        webbrowser.open(url)
        httpd.handle_request()

        return httpd.token_response


def refresh_token() -> dict[str, str]:
    """
    Refresh the existing token.

    Returns
    -------
    dict[str, str]
        The token data.
    """
    with open(SPOTIFY_TOKEN_FILE, "r") as f:
        refresh_token = json.load(f).get("refresh_token")

    if not refresh_token:
        token = request_token()

        with open(SPOTIFY_TOKEN_FILE, "w") as f:
            json.dump(token, f)

        return token

    data = {
        "grant_type": "refresh_token",
        "scope": "user-read-currently-playing",
        "refresh_token": refresh_token,
        "client_id": SPOTIFY_CLIENT_ID,
    }

    token = _post(SPOTIFY_TOKEN_ENDPOINT, SPOTIFY_TOKEN_HEADERS, data=data)

    with open(SPOTIFY_TOKEN_FILE, "w") as f:
        json.dump(token, f)

    return token


def get_song() -> dict[str, str]:
    """
    Request the current song.

    Returns
    -------
    dict[str, str]
        The response.
    """
    token = read_token()

    response = _get(
        "https://api.spotify.com/v1/me/player/currently-playing",
        {"Authorization": f"Bearer {token['access_token']}"},
    )

    if not response:
        log.warn("There is no song currently playing.")
        return response

    error = response.get("error", {})

    if error.get("message") == "The access token expired":
        log.info("Token expired. Requesting a new one")
        refresh_token()
        return get_song()

    return response


def format_song(response: dict[str, str], flags: Namespace) -> str:
    """
    Request the current song.

    Parameters
    ----------
    response: dict[str, str]
        The response from `get_song`.
    flags: Namespace
        The passed flags.

    Returns
    -------
    str
        The formatted song.
    """
    if (song := response["item"]) is None:
        no_song_msg = (
            "Maybe you are playing a podcast episode?"
            if response["context"] is None
            else "Maybe you got an ad?"
        )

        raise RuntimeError(no_song_msg)

    artist = song["artists"][0]["name"]
    name = song["name"]

    title = [f"{artist} - {name}"]

    if flags.album and song["album"]["album_type"] != "single":
        title.append(f"({song['album']['name']})")

    if flags.progress:
        progress_ms = response["progress_ms"]
        total_ms = song["duration_ms"]

        progress = __calc_time(progress_ms)
        total = __calc_time(total_ms)

        title.append(f"({progress} / {total})")

    return " ".join(title)
