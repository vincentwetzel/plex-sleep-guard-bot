# Architecture

The bot is one Python process running in a signed-in Windows user's session. It opens an outbound Discord Gateway connection and polls the configured Plex server. It has no GUI framework, Windows Service, inbound listener, input simulation, or last-input manipulation.

## Runtime components

- `config` loads environment values and `.env`, validates required Discord values, clamps configured durations, and resolves project-local paths.
- `plex` owns the `aiohttp` session and a 15-second bounded request to `/status/sessions`. It sends `X-Plex-Token` only when configured, parses direct XML children with a media `type`, and distinguishes failed requests from successful empty results.
- `playback` implements `IDLE`, `PLAYING`, and `GRACE_PERIOD` timing using monotonic seconds.
- `leases` combines playback/grace state and a manual deadline. It owns at most one native request and tracks manual requesters for expiry notifications.
- `power_windows` is the native boundary. It creates and clears the system-required power request, and reads the active plan's AC/DC sleep timeout plus current power source when an exit-status DM is prepared.
- `discord_bot` uses `discord.py` and only the non-privileged `guilds` intent. It defines the two slash commands and syncs them globally during startup.
- `notifications` persists the configured owner's enabled/disabled status-DM choice in project-local JSON. The owner is configured by `DISCORD_OWNER_USER_ID`; the bot does not enumerate guild members or maintain a Plex subscriber list.
- `service` runs independent Plex polling and one-second lease/grace expiry loops.
- `logging_setup` logs to the console and a project-local daily file, switches files at local midnight, and best-effort prunes files outside the seven-day retention window.
- `__main__` wires services together, logs a `powercfg /requests` snapshot about once per minute while protected, observes supervisor control markers, and closes tasks, leases, Plex, and Discord on exit.

## Plex state policy

A direct media child with a `type` is considered active unless its `state` is exactly `stopped` ignoring case. This includes `playing`, `paused`, missing-state, and buffering-like sessions. Only successful polls reach the state machine. A successful empty poll from `PLAYING` starts grace; active playback during grace returns the state to `PLAYING`. When grace elapses, the state becomes `IDLE`.

HTTP error statuses, network errors, timeouts, and invalid XML are failed observations. They preserve the prior state and grace deadline. In particular, a failed request does not mean playback ended and does not begin grace.

## Shared power request lifecycle

The request is active when either `PLAYING`/`GRACE_PERIOD` is active or the manual deadline has not elapsed. A new reason reuses the existing request. Expiry of one reason cannot clear the request while another reason remains.

When Plex transitions from `IDLE` to `PLAYING`, the configured owner receives a short DM that protection started and gives the grace-period duration. The owner receives a second DM only after a successful empty poll starts grace, the full configured grace duration elapses, and Plex remains `IDLE`; the empty poll itself does not send an end notice. Resumed playback cancels grace. Failed Plex polls preserve the state and grace deadline and do not send notices. The end DM includes the configured Windows inactivity timeout. When the current power source is known, it also gives a Discord-local approximate clock time assuming inactivity starts at the DM; this is an estimate, not a prediction, because Windows measures inactivity from user activity.

When the last combined reason ends, the coordinator clears and closes the native request. If at least one manual timer requester was recorded, the configured owner receives one concise guard-expiry DM with the configured inactivity timeout and, when possible, an approximate clock time under the same idle-from-now assumption. If the Windows settings cannot be read, the DM says so and still reports that the guard ended. Each event triggers one DM send attempt; failures are not queued for retry. Discord HTTP errors during DM delivery are logged and do not restore the lease. Successful DM sends are not logged. A manual timer can end before the combined guard; the expiry notice waits until Plex playback and grace also finish.

The app closes the lease in a `finally` cleanup path after controlled cancellation or a bot exit. Forced process termination bypasses Python cleanup; Windows normally drops process-owned requests when the process exits.

## Operating boundary

The adapter requests system-required behavior only. It does not keep the display on, override explicit sleep or shutdown, or help after power loss. The machine must already be awake and the bot connected to Discord to receive `/stay-awake`.
