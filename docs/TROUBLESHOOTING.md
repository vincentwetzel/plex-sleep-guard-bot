# Troubleshooting

Start with the current file in `logs/PlexSleepGuardBot-YYYY-MM-DD.log` under the project directory. Filenames use the local date. The handler keeps the current date and six preceding dates when it can; retention cleanup is best effort. Tokens are not written to the application log.

## The bot does not start

- Confirm the selected Python interpreter is version 3.12 or later and has `discord.py`, `aiohttp`, and `python-dotenv` installed. The launcher prefers `.venv\Scripts\python.exe` and otherwise uses the first `python.exe` on `PATH`.
- Confirm `.env` exists in the project root and includes `DISCORD_APPLICATION_ID` and `DISCORD_BOT_TOKEN`.
- Confirm the Application ID contains only a positive numeric ID and the token is current. If a token was reset in Discord, update the local `.env`.
- Confirm the project directory can create/write `logs/`; notification preferences are written under `state/` when changed.
- The native adapter requires Windows. It stops at startup on other platforms.

The start script runs the package source from `src`, so an editable project install is not required. To install the runtime libraries for a system Python, run `python -m pip install discord.py aiohttp python-dotenv`. For visible startup errors, open PowerShell, change to the project's `src` directory, then run `python -m plex_sleep_guard_bot`.

## The bot is offline or a slash command is missing

- Check that the process can make outbound connections to Discord's Gateway and API.
- Confirm the app is installed to the intended server with both `bot` and `applications.commands` scopes.
- Check the log for command sync errors. Commands sync globally and may take time to appear after first startup or an update.
- This app uses the non-privileged `guilds` intent. Message Content, Members, and Presence intents are not needed.
- Restart the bot after editing `.env`; configuration is loaded during process startup.

## Plex playback is not detected

- Confirm Plex is running and `PLEX_SERVER_URL` points to its base URL. The default is `http://127.0.0.1:32400`.
- Confirm the machine can access `/identity` at the configured server and that the server can answer `/status/sessions`.
- If the log reports HTTP 401 or 403, set or replace `PLEX_TOKEN` locally. A blank token is allowed only when the server permits the request.
- Polling is bounded by a 15-second timeout. HTTP errors, timeouts, network errors, and invalid XML count as failed polls.
- A failed poll intentionally preserves the last known state. It does not indicate that playback ended and does not begin grace.

## Windows still sleeps

While a lease should be active, run `powercfg /requests` in another terminal. The bot should appear under `SYSTEM:` with the PlexSleepGuardBot reason. While protected, it logs a request snapshot about once per minute. The app requests system-required behavior only; the display may still turn off.

Check that the `/stay-awake` response accepted the requested duration and that the timer is not expired. Plex playback or its grace period can independently keep the request active. Windows power plans or other system policy may affect sleep behavior.

The request cannot prevent explicit sleep or shutdown, power loss, or a machine that has already gone to sleep. Discord commands cannot wake the machine. The bot must already be running and connected before a command arrives.

## Guard-expiry DM was not received

- DMs go to users who requested a manual `/stay-awake` timer, and only when the combined Plex/manual guard fully releases.
- Notifications default to enabled. Run `/guard-notifications enabled:true` to ensure your preference is on; use `enabled:false` to turn it off.
- If a Plex lease remains after the manual timer ends, the combined guard has not expired and the DM waits.
- Discord privacy settings may block messages from server apps. Allow DMs from the app/server and make another request to confirm.
- The bot must remain connected until the combined guard expires. If it exits first, the OS request is cleaned up but no DM can be sent during that offline period.
- Preferences are stored in `state/guard_notification_preferences.json`; deleting the file resets everyone to the default enabled state.

## The supervisor does not start, stop, or restart

- Ensure `.venv` exists or that `python.exe` is on `PATH`; the selected interpreter also needs the three runtime dependencies.
- Start and stop scripts are in the project root. They use the same selected interpreter and `run/` directory.
- Check that the project is writable so the supervisor can create its lock, PID, and control markers under `run/`.
- Start requests restart of an existing supervised process. Stop requests graceful bot shutdown; the supervisor allows 25 seconds before it force-terminates a stuck process.
- A shortcut that should work with the stop script must launch `start_plex_sleep_guard_bot.bat`. A shortcut that launches `pythonw.exe` directly bypasses the supervisor and is not controlled by the start/stop scripts.
- If a stale marker remains after a crash, stop the supervisor, remove only the relevant marker under `run/`, then start again.

## The request was not cleared

The request should clear when Plex is `IDLE` and no manual deadline remains, and in the application's `finally` cleanup path during controlled shutdown. If the process was forcibly terminated, Windows normally removes process-owned requests when it exits. Check `powercfg /requests` after the process is gone. Do not use force termination for routine shutdown.
