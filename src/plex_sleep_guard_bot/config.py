"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc
    return min(max(value, minimum), maximum)


def _discord_id(name: str) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        raise ValueError(f"{name} is required.")
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a numeric Discord ID.") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive Discord ID.")
    return value


@dataclass(frozen=True, slots=True)
class AppConfig:
    discord_application_id: int
    discord_bot_token: str
    plex_server_url: str
    plex_token: str
    plex_poll_interval_seconds: int
    plex_grace_period_minutes: int
    stay_awake_max_minutes: int
    project_dir: Path
    log_dir: Path
    supervised: bool

    @classmethod
    def load(cls) -> AppConfig:
        """Load .env without overriding variables supplied by the environment."""
        load_dotenv(override=False)
        discord_token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
        if not discord_token:
            raise ValueError("DISCORD_BOT_TOKEN is required.")

        server_url = os.getenv("PLEX_SERVER_URL", "http://127.0.0.1:32400").strip().rstrip("/")
        parts = urlsplit(server_url)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            server_url = "http://127.0.0.1:32400"

        # This file is under <project>/src/plex_sleep_guard_bot.
        project_dir = Path(__file__).resolve().parents[2]
        log_dir = project_dir / "logs"

        return cls(
            discord_application_id=_discord_id("DISCORD_APPLICATION_ID"),
            discord_bot_token=discord_token,
            plex_server_url=server_url,
            plex_token=os.getenv("PLEX_TOKEN", "").strip(),
            plex_poll_interval_seconds=_int_env("PLEX_POLL_INTERVAL_SECONDS", 5, 1, 3600),
            plex_grace_period_minutes=_int_env("PLEX_GRACE_PERIOD_MINUTES", 15, 0, 1440),
            stay_awake_max_minutes=_int_env("STAY_AWAKE_MAX_MINUTES", 480, 1, 1440),
            project_dir=project_dir,
            log_dir=log_dir,
            supervised=os.getenv("PLEX_SLEEP_GUARD_SUPERVISED", "").strip() == "1",
        )
