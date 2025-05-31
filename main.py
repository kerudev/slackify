from time import sleep
from slack import get_presence, set_profile
from spotify import currently_playing_as_str

def main():
    while True:
        if get_presence().json()["presence"] == "away":
            return

        args = {"profile": {
            "status_text": currently_playing_as_str(),
            "status_emoji": ":musical_note:",
            "status_expiration": 0
        }}

        set_profile(args)

        sleep(2)

if __name__ == "__main__":
    main()
