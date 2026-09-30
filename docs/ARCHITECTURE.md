# Architecture

The bot is one Python process running in a signed-in Windows user's session. It opens an outbound Discord Gateway connection and polls the configured Plex server. It has no GUI framework, Windows Service, inbound listener, input simulation, or last-input manipulation.

## Runtime components

- `config` loads environment values and `.env`, validates required Discord values, clamps configured durations, and resolves project-local paths.
- `plex` owns the `aiohttp` session and a 15-second bounded request to `/status/sessions`. It sends `X-Plex-Token` only when configured, parses direct XML children with a media `type`, and distinguishes failed requests from successful empty results.
- `playback` implements `IDLE`, `PLAYING`, and `GRACE_PERIOD` timing using monotonic seconds.
- `leases` combines playback/grace state and a manual deadline. It owns at most one native request and tracks manual requesters for expiry notifications.
- `power_windows` is the only native boundary. It creates a request with `PowerCreateRequest`, sets `PowerRequestSystemRequired`, and clears/closes it through the request object's lifecycle.
- `discord_bot` uses `discord.py` and only the non-privileged `guilds` intent. It defines the two slash commands and syncs them globally during startup.
- `notifications` persists each user's enabled/disabled choice in project-local JSON. New users default to enabled.
- `service` runs independent Plex polling and one-second lease/grace expiry loops.
- `logging_setup` logs to the console and a project-local daily file, switches files at local midnight, and best-effort prunes files outside the seven-day retention window.
- `__main__` wires services together, logs a `powercfg /requests` snapshot about once per minute while protected, observes supervisor control markers, and closes tasks, leases, Plex, and Discord on exit.

## Plex state policy

A direct media child with a `type` is considered active unless its `state` is exactly `stopped` ignoring case. This includes `playing`, `paused`, missing-state, and buffering-like sessions. Only successful polls reach the state machine. A successful empty poll from `PLAYING` starts grace; active playback during grace returns the state to `PLAYING`. When grace elapses, the state becomes `IDLE`.

HTTP error statuses, network errors, timeouts, and invalid XML are failed observations. They preserve the prior state and grace deadline. In particular, a failed request does not mean playback ended and does not begin grace.

## Shared power request lifecycle

The request is active when either `PLAYING`/`GRACE_PERIOD` is active or the manual deadline has not elapsed. A new reason reuses the existing request. Expiry of one reason cannot clear the request while another reason remains.

When the last reason ends, the coordinator clears and closes the native request. It returns the recorded manual requester IDs; enabled requesters are then sent a DM. DM failure is logged and does not restore the lease. A manual timer can end before the combined guard: its requester stays recorded until Plex playback and grace also finish.

The app closes the lease in a `finally` cleanup path after controlled cancellation or a bot exit. Forced process termination bypasses Python cleanup; Windows normally drops process-owned requests when the process exits.

## Operating boundary

The adapter requests system-required behavior only. It does not keep the display on, override explicit sleep or shutdown, or help after power loss. The machine must already be awake and the bot connected to Discord to receive `/stay-awake`.
