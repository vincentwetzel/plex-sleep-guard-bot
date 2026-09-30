# Release notes

## 0.1.0 - Initial project implementation

- Established the separate `plex-sleep-guard-bot` Python package for Windows x64, with editable installation and a console entry point.
- Added environment and `.env` configuration for Discord credentials and Plex polling, grace, and manual duration settings.
- Implemented an async Plex session poller, XML parsing, conservative handling of failed polls, and an `IDLE`/`PLAYING`/`GRACE_PERIOD` state machine.
- Implemented a shared lease coordinator and a `ctypes` Windows adapter that holds one `PowerRequestSystemRequired` request for Plex playback/grace or a manual timer.
- Added globally synced Discord `/stay-awake` and `/guard-notifications` commands using a Gateway connection and no privileged intents.
- Added persisted per-user guard-expiry DM preferences. Notifications are enabled by default and sent to manual requesters after the combined guard releases.
- Added console logging and local-date files under `logs/`, midnight file switching, seven-day best-effort retention, and periodic `powercfg /requests` diagnostics.
- Added project-root Windows start/stop scripts and a hidden single-instance PowerShell supervisor with graceful control markers and restart after unexpected bot exits.
- Documented application setup, configuration, architecture, operation, safety limits, troubleshooting, and project follow-up work.

## Known initial limitations

- Automated tests have not been added.
- There is no standalone executable, installer, or automated release pipeline.
- Global Discord command registration can take time to propagate.
- Direct-message delivery depends on Discord privacy settings and the bot remaining connected when the guard expires.
