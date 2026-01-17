from pathlib import Path

VERSION = (0, 1, 0)

# Config and env vars stuff
CONFIG_PATH = Path.home() / ".config" / "slackfm"
CONFIG_PATH.mkdir(parents=True, exist_ok=True)

CONF_FILE = CONFIG_PATH / "slackfm.conf"
ENV_FILE = CONFIG_PATH / "slackfm.env"
PREV_PICTURE_FILE = CONFIG_PATH / "previous_profile_picture"

TOKEN_KEYS = ["SLACK_TOKEN", "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"]

# Service specific paths
TMP_SERVICE_PATH = Path("/tmp/slackfm.service")
SERVICE_PATH = Path("/usr/lib/systemd/system/slackfm.service")
