# Agent and contributor guidance

- Target Python 3.12+ and Windows x64; keep runtime dependencies limited to discord.py, aiohttp, and python-dotenv.
- Use Discord slash commands over a Gateway connection. Do not add privileged intents or an inbound listener.
- Never hardcode, print, or commit Discord or Plex tokens. Keep local secrets in ignored `.env`.
- Power inhibition is allowed only while Plex is `PLAYING`/`GRACE_PERIOD` or a manual timer is active. Use system-required behavior only; never inhibit the display.
- Combine all active reasons into one native power request and clear it on expiry and every controlled exit path.
- A failed Plex request must not be interpreted as playback ending.
- Keep core state/timing testable without native Windows power APIs; do not call those APIs from unit tests.
- Update README and docs when behavior, configuration, Discord installation, or troubleshooting changes.
- Document environment-variable overrides and supported commands as they are implemented.
