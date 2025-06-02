import os
import subprocess
import sys

from slackify import log

# Slackify's dir and entry
SLACKIFY_ENTRY = os.path.realpath(sys.argv[0])
SLACKIFY_DIR = os.path.dirname(SLACKIFY_ENTRY)

# Config and env vars stuff
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".config", "slackify")
os.makedirs(CONFIG_PATH, exist_ok=True)

CONF_FILE = os.path.join(CONFIG_PATH, "slackify.conf")
ENV_FILE = os.path.join(CONFIG_PATH, "slackify.env")
PREV_PICTURE_FILE = os.path.join(CONFIG_PATH, "previous_profile_picture")

# Config managements
if not os.path.exists(CONF_FILE):
    log.info(f"Creating config file at '{CONF_FILE}'")
    subprocess.run(["touch", CONF_FILE], check=True)

with open(CONF_FILE, "r") as f:
    lines = f.readlines()
    pairs = [line.strip().split("=") for line in lines]

    CONFIGURATION = {pair[0].lower(): pair[1].lower() in ("true", "1") for pair in pairs}

# Env vars managements
if not os.path.exists(ENV_FILE):
    log.info(f"Creating env file at '{ENV_FILE}'")
    subprocess.run(["touch", ENV_FILE], check=True)

with open(ENV_FILE, "r") as f:
    lines = f.readlines()
    pairs = [line.strip().split("=") for line in lines]

    FILE_TOKENS = {pair[0].upper(): pair[1] for pair in pairs}

# Credentials
KEY_SLACK_TOKEN = "SLACK_TOKEN"
KEY_SPOTIFY_CLIENT_ID = "SPOTIFY_CLIENT_ID"
KEY_SPOTIFY_CLIENT_SECRET = "SPOTIFY_CLIENT_SECRET"

TOKEN_KEYS = [KEY_SLACK_TOKEN, KEY_SPOTIFY_CLIENT_ID, KEY_SPOTIFY_CLIENT_SECRET]
CREDENTIALS = {
    key: value
    for key in TOKEN_KEYS
    if (value := os.getenv(key) or FILE_TOKENS.get(key))
}

# Service specific paths
TMP_SERVICE_PATH = "/tmp/slackify.service"
SERVICE_PATH = "/usr/lib/systemd/system/slackify.service"

# URLs
SLACK_URL = "https://slack.com/api"
SPOTIFY_TOKEN_ENDPOINT = "https://accounts.spotify.com/api/token"

# Spotify token management
SPOTIFY_TOKEN_PATH = os.path.join(SLACKIFY_DIR, "tokens")
SPOTIFY_TOKEN_FILE = os.path.join(SPOTIFY_TOKEN_PATH, "spotify_token.json")
