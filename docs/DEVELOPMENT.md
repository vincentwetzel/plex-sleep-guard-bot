# Development and operation

## Requirements

- Windows x64 for the native power adapter and launcher scripts.
- Python 3.12 or later.
- A Discord application installed to a test server and a Plex server reachable from this machine.

## Create a development environment

Run these commands from the project root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
Copy-Item .env.example .env
```

Fill in the local `.env` using [Discord setup](DISCORD_SETUP.md) and [configuration](CONFIGURATION.md). Never put real tokens in source files, command history, logs, screenshots, or support messages.

## Run and stop

For a visible development session, run:

```powershell
python -m plex_sleep_guard_bot
```

The installed `plex-sleep-guard-bot` console command uses the same entry point. Ctrl+C initiates cancellation and cleanup. On Windows, `start_plex_sleep_guard_bot.bat` launches a hidden PowerShell supervisor using the selected Python interpreter and restarts after unexpected bot exits. Running the start script again requests a graceful restart. `stop_plex_sleep_guard_bot.bat` requests a graceful stop. The bot checks markers under `run/`, closes its Discord and Plex clients, and clears its native request during cleanup. The supervisor waits up to 25 seconds before force-terminating a stuck bot.

The start script uses `.venv\Scripts\python.exe` when it exists. Otherwise, it uses the first `python.exe` found on `PATH`. The supervisor runs the package from the project's `src` directory, so an editable project install is not required. The selected interpreter must be Python 3.12 or later and have `discord.py`, `aiohttp`, and `python-dotenv` installed. For a system Python, install those runtime dependencies with `python -m pip install discord.py aiohttp python-dotenv` from the project root. Runtime logs live in `logs/`; preferences live in `state/`. Those directories and `run/` are ignored by Git.

To create a Windows shortcut that works with `stop_plex_sleep_guard_bot.bat`, set the shortcut target to `start_plex_sleep_guard_bot.bat` and **Start in** to the project root. Launching `pythonw.exe` directly starts an unsupervised bot process; the project's stop script only signals the supervisor and will not control that process.

## Command registration and Discord access

Application commands sync globally whenever the bot starts. First registration and command edits may take time to appear. The app needs outbound connectivity to Discord's Gateway and API. It uses the non-privileged `guilds` intent; Message Content, Members, and Presence intents are not required.

## Validation status

There is currently no automated test suite. When tests are added, XML parsing, failed-poll behavior, state transitions, timer boundaries, lease aggregation, configuration, notification persistence, and log retention should be covered deterministically. Core tests should use a fake power manager and must not call Windows native APIs.

Manually validate the Windows adapter on a test PC by starting a Plex or manual lease and running `powercfg /requests`. The app should appear under `SYSTEM:` with its PlexSleepGuardBot reason. Confirm that the request clears after all reasons end and after a graceful stop. The `DISPLAY:` category should not contain an app request.

## Packaging and release

The repository currently provides a source package installable with `pip install -e .`; it does not produce a Windows installer or standalone executable. Review [release notes](RELEASE_NOTES.md) and [project status](PROJECT_OUTLINE.md) before preparing a distributable release.
