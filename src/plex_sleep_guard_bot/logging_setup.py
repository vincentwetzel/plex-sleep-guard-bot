"""Console and date-named daily file logging with seven-day cycling."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import TextIO


class DatedDailyFileHandler(logging.Handler):
    """Write each local calendar day to its own dated file and prune old files."""

    terminator = "\n"

    def __init__(self, log_dir: Path, backup_days: int = 7) -> None:
        super().__init__()
        if backup_days < 1:
            raise ValueError("backup_days must be at least 1")
        self.log_dir = log_dir
        self.backup_days = backup_days
        self._active_date: date | None = None
        self._stream: TextIO | None = None
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._switch_day(date.today())

    def emit(self, record: logging.LogRecord) -> None:
        try:
            current_date = date.today()
            if current_date != self._active_date:
                self._switch_day(current_date)
            if self._stream is None:
                raise OSError("Daily log file is not open.")
            self._stream.write(self.format(record) + self.terminator)
            self._stream.flush()
        except Exception:
            self.handleError(record)

    def _switch_day(self, current_date: date) -> None:
        self._close_stream()
        file_path = self.log_dir / f"PlexSleepGuardBot-{current_date:%Y-%m-%d}.log"
        self._stream = file_path.open("a", encoding="utf-8", errors="backslashreplace")
        self._active_date = current_date
        self._prune(current_date)

    def _prune(self, current_date: date) -> None:
        cutoff = current_date - timedelta(days=self.backup_days - 1)
        prefix = "PlexSleepGuardBot-"
        for path in self.log_dir.glob(f"{prefix}????-??-??.log"):
            date_text = path.stem.removeprefix(prefix)
            try:
                file_date = date.fromisoformat(date_text)
            except ValueError:
                continue
            if file_date < cutoff:
                try:
                    path.unlink()
                except OSError:
                    # Retention is best effort; a locked file must not stop logging.
                    pass

    def _close_stream(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            stream.close()

    def close(self) -> None:
        self._close_stream()
        super().close()


def configure_logging(log_dir: Path) -> None:
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = DatedDailyFileHandler(log_dir, backup_days=7)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
