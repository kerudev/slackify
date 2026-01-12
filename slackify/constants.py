from pathlib import Path

VERSION = (0, 1, 0)

# Config and env vars stuff
CONFIG_PATH = Path.home() / ".config" / "slackify"
CONFIG_PATH.mkdir(parents=True, exist_ok=True)

CONF_FILE = CONFIG_PATH / "slackify.conf"
ENV_FILE = CONFIG_PATH / "slackify.env"
PREV_PICTURE_FILE = CONFIG_PATH / "previous_profile_picture"

TOKEN_KEYS = ["SLACK_TOKEN", "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"]

# Service specific paths
TMP_SERVICE_PATH = Path("/tmp/slackify.service")
SERVICE_PATH = Path("/usr/lib/systemd/system/slackify.service")

LIB_HEADERS = {
    "User-Agent": f"slackify/{'.'.join(str(x) for x in VERSION)} (+https://github.com/kerudev/slackify)",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "*/*",
    "Connection": "keep-alive",
}
