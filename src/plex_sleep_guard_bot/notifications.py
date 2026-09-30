"""Persistent per-user preference for guard-expiry direct messages."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class NotificationPreferences:
    """Store opt-out preferences locally; notifications are enabled by default."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._enabled_by_user: dict[int, bool] = {}
        self._load()

    def enabled_for(self, user_id: int) -> bool:
        return self._enabled_by_user.get(user_id, True)

    def set_enabled(self, user_id: int, enabled: bool) -> None:
        previous = self._enabled_by_user.get(user_id)
        self._enabled_by_user[user_id] = enabled
        temporary_path = self.file_path.with_suffix(self.file_path.suffix + ".tmp")
        serialized = json.dumps(
            {str(key): value for key, value in sorted(self._enabled_by_user.items())},
            indent=2,
        )
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(serialized + "\n", encoding="utf-8")
            temporary_path.replace(self.file_path)
        except OSError:
            if previous is None:
                self._enabled_by_user.pop(user_id, None)
            else:
                self._enabled_by_user[user_id] = previous
            raise

    def _load(self) -> None:
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            logger.warning("Could not load guard notification preferences: %s", exc)
            return

        if not isinstance(data, dict):
            logger.warning("Guard notification preferences are invalid; using defaults.")
            return
        for raw_user_id, enabled in data.items():
            try:
                user_id = int(raw_user_id)
            except (TypeError, ValueError):
                continue
            if user_id > 0 and isinstance(enabled, bool):
                self._enabled_by_user[user_id] = enabled
