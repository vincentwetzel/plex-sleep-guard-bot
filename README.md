# Plex Sleep Guard Bot

Plex Sleep Guard Bot is a Windows x64 Discord bot that monitors Plex playback and accepts bounded `/stay-awake minutes:<integer>` requests. Plex playback and its post-playback grace period share one Windows system-required power request with manual timers. The display is not inhibited.

The bot uses Python 3.12+, `discord.py`, `aiohttp`, `python-dotenv`, and a small `ctypes` adapter for the Windows Power Request API. Discord interactions arrive over the outbound Gateway connection. The bot does not need privileged Gateway intents or an inbound listener.

## What it does

- Keeps the PC from automatically sleeping while Plex reports active playback, during a configurable grace period after playback, or while a manual timer is active.
- Treats every Plex media session whose state is not `stopped` as active, including paused or buffering sessions.
- Starts the grace period only after a successful Plex poll reports no active sessions. Failed HTTP requests, timeouts, network errors, and invalid XML preserve the last known state.
- Combines Plex and manual reasons into one system-required power request. The request clears when no reason remains and during controlled shutdown cleanup.
- Sends a direct message to each manual timer requester when the combined guard finally expires. Notifications are enabled by default and can be changed with `/guard-notifications enabled:false` or `/guard-notifications enabled:true`.

The request does not keep the display on and cannot override explicit sleep or shutdown, power loss, or an already sleeping machine. The bot must be running and connected to Discord to receive commands; it cannot wake the PC.

## Requirements

- Windows x64 and Python 3.12 or later.
- A Discord application installed to a server with the `bot` and `applications.commands` scopes.
- A Plex server reachable from the bot machine. `PLEX_TOKEN` is optional for a server that allows unauthenticated session polling.

See [Discord application setup](docs/DISCORD_SETUP.md) for creating the app, handling its credentials, installing it, and registering commands.

## Install and run

From the project root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
Copy-Item .env.example .env
```

Edit `.env` with the Discord Application ID, bot token, and Plex settings. Keep the file private. Then start the bot:

```powershell
python -m plex_sleep_guard_bot
```

The installed console command `plex-sleep-guard-bot` starts the same entry point. For an unattended hidden process, use the root-level `start_plex_sleep_guard_bot.bat`; use `stop_plex_sleep_guard_bot.bat` for a graceful stop. See [development and operation](docs/DEVELOPMENT.md) for supervisor behavior.

The start script prefers `.venv\Scripts\python.exe`, then falls back to the first `python.exe` on `PATH`. It runs the package from the `src` directory, so an editable project install is not required. The selected Python 3.12+ interpreter must have `discord.py`, `aiohttp`, and `python-dotenv` installed; if needed, install them with `python -m pip install discord.py aiohttp python-dotenv`.

For a Windows shortcut that remains manageable by the stop script, set its target to `start_plex_sleep_guard_bot.bat` and its **Start in** directory to the project root. A shortcut that runs `pythonw.exe` directly bypasses the supervisor, so the project stop script will not stop that process.

Application commands are always synced globally. They can take time to appear in Discord after the first start or after command changes.

## Commands

| Command | Behavior |
| --- | --- |
| `/stay-awake minutes:<integer>` | Starts or extends a manual timer. The accepted range is 1 through `STAY_AWAKE_MAX_MINUTES` (default 480). The response is private. |
| `/guard-notifications enabled:<true/false>` | Saves whether your account receives a DM when its manual requester's combined guard expires. The response is private. |

An active manual request can outlast its requested timer when Plex playback or its grace period still holds the shared guard. In that case the requester's expiry DM waits until the final reason ends. Notification preferences are stored locally in `state/guard_notification_preferences.json` and default to enabled.

## Project data

- Daily logs: `logs/PlexSleepGuardBot-YYYY-MM-DD.log` under the project directory. A new file is opened at local midnight; files older than seven days are pruned when possible.
- Notification preferences: `state/guard_notification_preferences.json`.
- Supervisor lock, PID, and stop/restart markers: `run/`.

All three directories are Git-ignored. No credentials, logs, preferences, or control files are stored under `%LocalAppData%`.

## Documentation

- [Project outline and status](docs/PROJECT_OUTLINE.md)
- [Architecture and lease lifecycle](docs/ARCHITECTURE.md)
- [Configuration](docs/CONFIGURATION.md)
- [Development and operation](docs/DEVELOPMENT.md)
- [Discord application setup](docs/DISCORD_SETUP.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Release notes](docs/RELEASE_NOTES.md)

## Credentials and scope

Keep Discord and Plex secrets in the ignored local `.env` or a deployment secret store. Never commit or print tokens. This project does not add a GUI framework, Windows Service, inbound listener, input simulation, or last-input manipulation.
