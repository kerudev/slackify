import base64
import http.server
import json
import os
import socketserver
import webbrowser
import requests
import random
import string

import urllib

from datetime import datetime

SPOTIFY_TOKEN_PATH = "spotify_token.json"
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

PORT = 8888
REDIRECT_URI = f'http://127.0.0.1:{PORT}/callback'

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.token_response = None

class SpotifyTokenHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        query = urllib.parse.parse_qs(parsed.query)
        code = query.get('code', [''])[0]

        self.send_response(302)
        self.send_header('Location', 'https://open.spotify.com/')
        self.end_headers()

        token_url = 'https://accounts.spotify.com/api/token'
        data = urllib.parse.urlencode({
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI,
        }).encode()

        credentials = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
        headers = {
            'Authorization': 'Basic ' + base64.b64encode(credentials.encode()).decode(),
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        req = urllib.request.Request(token_url, data=data, headers=headers)
        with urllib.request.urlopen(req) as res:
            self.server.token_response = json.loads(res.read().decode())

def __get_state() -> str:
    chars = string.ascii_uppercase + string.digits
    size = 16

    return ''.join(random.choice(chars) for _ in range(size))

def __calc_time(millis: int) -> str:
    total_secs = millis / 1000

    mins = total_secs // 60
    secs = total_secs % 60

    return f"{mins}:{secs:02d}"

def get_token() -> dict[str, str]:
    now = datetime.now()

    if os.path.exists(SPOTIFY_TOKEN_PATH):
        with open(SPOTIFY_TOKEN_PATH, "r") as f:
            token = json.load(f)

        expire_date = datetime.strptime(token["expire_date"], "%Y-%m-%d %H:%M:%S")

        if expire_date < now:
            return token

    token = request_token()
    token["expire_date"] = now.strftime("%Y-%m-%d %H:%M:%S")

    with open(SPOTIFY_TOKEN_PATH, "w") as f:
        json.dump(token, f)

    return token

def request_token() -> dict[str, str]:
    with ReusableTCPServer(("", PORT), SpotifyTokenHandler) as httpd:
        params = {
            'response_type': 'code',
            'client_id': SPOTIFY_CLIENT_ID,
            'scope': "user-read-currently-playing",
            'redirect_uri': REDIRECT_URI,
            'state': __get_state(),
        }

        webbrowser.open('https://accounts.spotify.com/authorize?' + urllib.parse.urlencode(params))
        httpd.handle_request()

        return httpd.token_response

def get_song() -> requests.Response:
    token = get_token()
    access_token = token["access_token"]

    return requests.get(
        url="https://api.spotify.com/v1/me/player/currently-playing",
        headers={"Authorization": f"Bearer {access_token}"}
    )

def currently_playing_as_str() -> str:
    response = get_song().json()

    song = response["item"]

    artist = song["artists"][0]["name"]
    name = song["name"]
    album = song["album"]["name"]

    progress_ms = response["progress_ms"]
    total_ms = song["duration_ms"]

    progress = __calc_time(progress_ms)
    total = __calc_time(total_ms)

    # return f"{artist} - {name} ({album})"
    return f"{artist} - {name} ({progress} / {total})"
