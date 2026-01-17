import base64
import http.server
import json
import os
import random
import socketserver
import string
from time import sleep
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

SPOTIFY_ENCODED_AUTH = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()

SPOTIFY_TOKEN_HEADERS = {
    "Authorization": f"Basic {SPOTIFY_ENCODED_AUTH}",
    "Content-Type": "application/x-www-form-urlencoded",
}

# Used to request the token for the first time (or if it isn't stored in a file)
PORT = 8888
REDIRECT_URI = f"http://127.0.0.1:{PORT}/callback"

def __calc_time(millis: int) -> str:
    total_secs = millis // 1000

    mins = total_secs // 60
    secs = total_secs % 60

    return f"{mins}:{secs:02d}"


def _get(url: str, headers: dict[str, Any]) -> str:
    req = urllib.request.Request(
        url=url,
        headers=headers,
        method="GET",
    )

    return dispatch(req)

def _post(url: str, json: dict[str, Any], headers: dict[str, Any]) -> str:
    data = urllib.parse.urlencode(json).encode()

    req = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
    )

    return dispatch(req)

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self):
        super().__init__(("", PORT), SpotifyTokenHandler)
        self.token_response = None

class SpotifyTokenHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
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

        response = _post(
            url=SPOTIFY_TOKEN_ENDPOINT,
            json=data,
            headers=SPOTIFY_TOKEN_HEADERS,
        )

        self.server.token_response = response

def read_token() -> dict[str, str]:
    if SPOTIFY_TOKEN_FILE.exists():
        with open(SPOTIFY_TOKEN_FILE, "r") as f:
            return json.load(f)

    token = request_token()

    with open(SPOTIFY_TOKEN_FILE, "w") as f:
        json.dump(token, f)

    return token

def request_token() -> dict[str, str]:
    chars = string.ascii_uppercase + string.digits
    state = "".join(random.choice(chars) for _ in range(16))

    params = {
        "response_type": "code",
        "client_id": SPOTIFY_CLIENT_ID,
        "scope": "user-read-currently-playing",
        "redirect_uri": REDIRECT_URI,
        "state": state,
    }

    with ReusableTCPServer() as httpd:
        webbrowser.open("https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params))
        httpd.handle_request()

        return httpd.token_response

def refresh_token() -> dict[str, str]:
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

    token = _post(
        url=SPOTIFY_TOKEN_ENDPOINT,
        json=data,
        headers=SPOTIFY_TOKEN_HEADERS,
    )

    with open(SPOTIFY_TOKEN_FILE, "w") as f:
        json.dump(token, f)

    return token

def get_song() -> str:
    token = read_token()

    response = _get(
        url="https://api.spotify.com/v1/me/player/currently-playing",
        headers={"Authorization": f"Bearer {token['access_token']}"},
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

def song_as_str(song_response: dict[str, str], flags: Namespace) -> str | bool:
    try:
        if (song := song_response["item"]) == None:
            if song_response["context"] == None:
                log.info("There is no song playing. Maybe you are playing a podcast episode?")
                log.info("Stopping the service")

                return True

            log.info("There is no song playing. Maybe you got an ad?")
            log.info("Sleeping for 5 seconds until the ads end")
            sleep(5)

        artist = song["artists"][0]["name"]
        name = song["name"]

        title = [f"{artist} - {name}"]

        if flags.album and song["album"]["album_type"] != "single":
            title.append(f"({song['album']['name']})")

        if flags.progress:
            progress_ms = song_response["progress_ms"]
            total_ms = song["duration_ms"]

            progress = __calc_time(progress_ms)
            total = __calc_time(total_ms)

            title.append(f"({progress} / {total})")

        return " ".join(title)

    except KeyError as ke:
        log.err(f"The following key is missing: {ke}")
        log.err(song_response)

        return True
