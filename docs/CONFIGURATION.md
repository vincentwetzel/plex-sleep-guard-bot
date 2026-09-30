# Configuration

For local use, copy `.env.example` to `.env`. `python-dotenv` loads it without replacing environment variables already supplied to the process. Keep `.env` private; `.env*` is ignored by Git except for the example template.

| Variable | Default | Purpose and validation |
| --- | --- | --- |
| `DISCORD_APPLICATION_ID` | required | Positive numeric Application ID from the Developer Portal. Used to identify the app and register commands. |
| `DISCORD_BOT_TOKEN` | required | Bot credential. Never log, commit, or share it. |
| `PLEX_SERVER_URL` | `http://127.0.0.1:32400` | Plex base URL. Values without an `http` or `https` scheme or network location fall back to the default. |
| `PLEX_TOKEN` | empty | Optional token sent in the `X-Plex-Token` request header. |
| `PLEX_POLL_INTERVAL_SECONDS` | `5` | Poll period; values are clamped to 1–3600 seconds. |
| `PLEX_GRACE_PERIOD_MINUTES` | `15` | Post-playback grace; values are clamped to 0–1440 minutes. `0` ends the Plex lease as soon as a successful empty poll arrives. |
| `STAY_AWAKE_MAX_MINUTES` | `480` | Maximum accepted `/stay-awake` duration; values are clamped to 1–1440 minutes. |

Missing or malformed required Discord values stop startup with an error. Non-integer duration values also stop startup; integers outside documented bounds are clamped. Malformed URL syntax can stop startup; values with an unsupported or missing scheme/network location fall back to the localhost default. Tokens are not included in application log messages. Commands are always synced globally and can take time to appear after startup or an edit.

`PLEX_SLEEP_GUARD_SUPERVISED` is an internal process flag. The root supervisor sets it to `1` so the bot watches `run/` for stop/restart requests. Leave it unset for a normal manual run; it is not a user tuning option.

## Local data and logs

All writable runtime data is in the project directory:

- `logs/PlexSleepGuardBot-YYYY-MM-DD.log`: local-date log files. Logging changes files at midnight and tries to retain the current date plus the prior six dates. Pruning is best effort if a file is locked.
- `state/guard_notification_preferences.json`: per-user DM preferences; missing users default to enabled.
- `run/`: supervisor lock/PID and stop/restart markers.

These folders are Git-ignored. The bot does not store logs or preferences under `%LocalAppData%`.

Use `/guard-notifications enabled:false` to disable guard-expiry DMs for your Discord account, or `/guard-notifications enabled:true` to re-enable them. The setting is saved locally and checked when the combined Plex/manual guard releases.
