import base64
import http.server
import json
import os
import random
import socketserver
import string
import urllib.request
import webbrowser
from argparse import Namespace
from typing import Optional

import requests

from slackify import log
from slackify.constants import (
    CREDENTIALS,
    KEY_SPOTIFY_CLIENT_ID,
    KEY_SPOTIFY_CLIENT_SECRET,
    SPOTIFY_TOKEN_ENDPOINT,
    SPOTIFY_TOKEN_FILE,
    SPOTIFY_TOKEN_PATH
)


SPOTIFY_CLIENT_ID = CREDENTIALS[KEY_SPOTIFY_CLIENT_ID]
SPOTIFY_CLIENT_SECRET = CREDENTIALS[KEY_SPOTIFY_CLIENT_SECRET]

# Used to request the token for the first time (or if it isn't stored in a file)
PORT = 8888
REDIRECT_URI = f"http://127.0.0.1:{PORT}/callback"

os.makedirs(SPOTIFY_TOKEN_PATH, exist_ok=True)

def __calc_time(millis: int) -> str:
    total_secs = millis // 1000

    mins = total_secs // 60
    secs = total_secs % 60

    return f"{mins}:{secs:02d}"

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self):
        server_address = ("", PORT)
        RequestHandlerClass = SpotifyTokenHandler
        
        super().__init__(server_address, RequestHandlerClass)
        self.token_response = None

class SpotifyTokenHandler(http.server.BaseHTTPRequestHandler):
    @staticmethod
    def token_headers():
        credentials = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
        headers = {
            "Authorization": "Basic " + base64.b64encode(credentials.encode()).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        return headers

    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", "https://open.spotify.com/")
        self.end_headers()

        parsed = urllib.parse.urlparse(self.path)

        query = urllib.parse.parse_qs(parsed.query)
        code = query.get("code", [""])[0]

        data = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        }).encode()

        req = urllib.request.Request(
            SPOTIFY_TOKEN_ENDPOINT,
            data=data,
            headers=self.token_headers(),
        )

        with urllib.request.urlopen(req) as res:
            self.server.token_response = json.loads(res.read().decode())

def get_token() -> dict[str, str]:
    if os.path.exists(SPOTIFY_TOKEN_FILE):
        with open(SPOTIFY_TOKEN_FILE, "r") as f:
            return json.load(f)

    token = request_token()

    with open(SPOTIFY_TOKEN_FILE, "w") as f:
        json.dump(token, f)

    return token

def request_token() -> dict[str, str]:
    chars = string.ascii_uppercase + string.digits
    state = "".join(random.choice(chars) for _ in range(16))

    with ReusableTCPServer() as httpd:
        params = {
            "response_type": "code",
            "client_id": SPOTIFY_CLIENT_ID,
            "scope": "user-read-currently-playing",
            "redirect_uri": REDIRECT_URI,
            "state": state,
        }

        webbrowser.open("https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params))
        httpd.handle_request()

        return httpd.token_response

def refresh_token() -> dict[str, str]:
    with open(SPOTIFY_TOKEN_FILE, "r") as f:
        refresh_token = json.load(f)["refresh_token"]

    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": SPOTIFY_CLIENT_ID,
    }).encode()

    req = urllib.request.Request(
        SPOTIFY_TOKEN_ENDPOINT,
        data=data,
        headers=SpotifyTokenHandler.token_headers(),
    )

    with urllib.request.urlopen(req) as res:
        token = json.loads(res.read().decode())

    with open(SPOTIFY_TOKEN_FILE, "w") as f:
        json.dump(token, f)

    return token

def get_song() -> requests.Response:
    token = get_token()
    access_token = token["access_token"]

    response = requests.get(
        url="https://api.spotify.com/v1/me/player/currently-playing",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if not response.content.decode():
        log.warn("There is no song currently playing.")
        return response

    error = response.json().get("error")

    if error and error.get("message") == "The access token expired":
        log.info("Token expired. Requesting a new one")
        refresh_token()
        return get_song()

    return response

def song_as_str(flags: Optional[Namespace] = None) -> str:
    response = get_song()

    if not response.content:
        return

    response_json = response.json()

    try:
        song = response_json["item"]

        artist = song["artists"][0]["name"]
        name = song["name"]

        title = [f"{artist} - {name}"]

        if flags.album and song["album"]["album_type"] != "single":
            title.append(f"({song["album"]["name"]})")

        if flags.progress:
            progress_ms = response_json["progress_ms"]
            total_ms = song["duration_ms"]

            progress = __calc_time(progress_ms)
            total = __calc_time(total_ms)

            title.append(f"({progress} / {total})")

        return " ".join(title)
    
    except KeyError as ke:
        log.err(f"The following key is missing: {ke}")
        log.err(response_json)

        return ""
