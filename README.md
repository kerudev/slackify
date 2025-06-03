# Slackify

Slackify is a lightweight script that updates your Slack status with the song
you're currently playing on Spotify.

It features:
- Zero dependencies.
- Service creation and management using systemctl.
- Various commands to use Slackify.
- Flags and configuration file to control the program's behavior.
- Automatic token refreshing for Spotify.

## Credentials

Credentials are needed to connect to the Slack workspace and get permission from
the Spotify user account. Here is a quick guide on how I got them:

### Slack

1. Go to `https://api.slack.com/apps`
2. Click on `Create an App` -> `From scratch`
3. Fill the `App Name` and `Pick a workspace to develop your app in` inputs
4. OAuth & Permissions
  - Scopes -> User Token Scopes
    - users:read
    - users:write
    - users.profile:read
    - users.profile:write
  - OAuth Tokens -> Install to [`Your workspace name`]
5. Click on `Allow`
6. You can get the token back at the `OAuth Tokens` section.

### Spotify

1. Go to `https://developer.spotify.com/dashboard` -> Accept the terms
2. `Create app`
  - Fill `App name` and `App description`
  - Write `http://127.0.0.1:8888/callback` in `Redirect URIs`
  - Tick the `Web API` box
3. Accept the terms and click on `Save`
4. The next screen will contain both the Client ID and Client Secret.

## How to use

### play

Initializes slackify in the current shell session.

It accepts the following flags:
  - `album`: displays the song's album title (if it's not a single)
  - `progress`: displays the current progress through the song
  - `cover`: temporarily sets your profile picture to the song's cover

### init

Creates the following files:
- `/usr/lib/systemd/system/slackify.service`: the Slackify service itself.\
It is used through `./slackify.py start` and `./slackify.py stop`.
Also reloads the all unit files by running `sudo systemctl daemon-reload`.

- `~/.config/slackify/slackify.conf`: contains the service's configuration.\
It it changes, the service has to stop so the changes are applied.
The allowed values are the same as the `play` flags. 
```conf
album=true
progress=false
cover=true
```

- `~/.config/slackify/slackify.env`: contains the previously mentioned credentials.
```env
SLACK_TOKEN=your-slack-token
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
```

### status

Runs `systemctl is-active slackify.service`.

### start

Runs `sudo systemctl start slackify.service`, which is the same as
calling `./slackify.py play` but from a service. Arguments will be read from
`~/.config/slackify/slackify.conf`.

### stop

Runs `sudo systemctl stop slackify.service`.

### reset

Runs `sudo systemctl stop slackify.service`, then `sudo systemctl start slackify.service`.
