# Project outline

## Purpose

Keep a Windows PC from automatically sleeping while Plex reports active playback, during a configurable post-playback grace period, or for a bounded duration requested with Discord `/stay-awake minutes:<integer>`.

## Current status

The initial runtime and operator documentation are implemented. The project can be installed as a Python package, run directly or through its Windows supervisor scripts, and configured through environment variables or a local `.env` file. It does not yet include an automated test suite, installer, or release workflow.

## Repository layout

```text
src/plex_sleep_guard_bot/
  __init__.py
  __main__.py            # startup, tasks, cancellation, cleanup
  config.py              # dotenv/environment loading and range validation
  plex.py                # bounded aiohttp poll and XML session parsing
  playback.py            # IDLE/PLAYING/GRACE_PERIOD state machine
  leases.py              # Plex and manual reasons combined into one request
  power_windows.py       # ctypes PowerCreateRequest/Set/Clear adapter
  discord_bot.py         # Gateway client and global slash commands
  notifications.py       # persisted per-user expiry DM preferences
  logging_setup.py       # console and dated file logging/retention
  service.py             # Plex polling and lease-expiry loops
docs/                    # setup, operation, architecture, troubleshooting
start_plex_sleep_guard_bot.bat
stop_plex_sleep_guard_bot.bat
supervise_plex_sleep_guard_bot.ps1
```

## Component responsibilities

- **Configuration:** load secrets from environment or `.env`, validate the Discord Application ID, apply documented numeric bounds, and resolve project-local data paths.
- **Plex poller:** request `/status/sessions` with `X-Plex-Token` when configured, apply a finite timeout, and distinguish a successful observation from a failed poll.
- **Playback state machine:** consume successful observations only. A non-stopped session is active. A successful empty result starts grace; renewed playback cancels grace.
- **Lease coordinator:** combine `PLAYING`/`GRACE_PERIOD` and the manual deadline into one native request. Keep the request until both reasons end.
- **Windows adapter:** use `PowerRequestSystemRequired` only; it never requests display-required behavior.
- **Discord bot:** use the Gateway with non-privileged intents, sync commands globally, validate manual durations, and provide private command responses.
- **Notifications:** save per-user DM preferences in project-local state. Notify manual requesters only after the combined guard releases.
- **Lifecycle and logging:** run polling, expiry, and status tasks; clear the request through controlled shutdown cleanup; write console and dated project logs; prune old logs.
- **Windows supervisor:** maintain one hidden supervisor, restart after unexpected bot exit, and support graceful stop/restart markers.

## Lease model

```text
successful active Plex poll ───────┐
                                   ├─ any reason active -> one system-required request
manual timer not expired ──────────┘

successful empty poll -> GRACE_PERIOD -> expiry -> Plex reason ends
failed Plex poll -> preserve prior playback state and grace deadline
manual timer expiry -> manual reason ends
all reasons ended -> clear request and DM opted-in manual requesters
```

If one reason ends while another remains active, the native request remains set. A manual requester is notified only after every guard reason ends, even if the manual timer itself expired earlier.

## Follow-up work

1. Add deterministic automated tests for XML parsing, failed-poll conservatism, state transitions, lease aggregation, configuration, notifications, and log retention.
2. Exercise the native adapter on Windows and confirm its entry under `SYSTEM:` using `powercfg /requests`.
3. Choose a packaged distribution and release process after validating the runtime on the target machine.
