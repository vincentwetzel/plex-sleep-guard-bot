"""Combine all active reasons into a single Windows power request."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from .playback import PlaybackState

logger = logging.getLogger(__name__)
POWER_REQUEST_REASON = "PlexSleepGuardBot Plex playback/grace or Discord stay-awake timer"


class PowerRequest(Protocol):
    def close(self) -> None: ...


class PowerRequestFactory(Protocol):
    def __call__(self, reason: str) -> PowerRequest: ...


@dataclass(frozen=True, slots=True)
class GuardExpired:
    notification_user_ids: tuple[int, ...]


class LeaseCoordinator:
    """Event-loop-confined owner of the app's one and only native request."""

    def __init__(self, request_factory: PowerRequestFactory) -> None:
        self._request_factory = request_factory
        self._request: PowerRequest | None = None
        self._playback_state = PlaybackState.IDLE
        self._manual_until: float | None = None
        self._manual_requesters: set[int] = set()

    @property
    def request_active(self) -> bool:
        return self._request is not None

    @property
    def manual_until(self) -> float | None:
        return self._manual_until

    @property
    def playback_state(self) -> PlaybackState:
        return self._playback_state

    def set_playback_state(self, state: PlaybackState, now: float) -> GuardExpired | None:
        self._playback_state = state
        return self.advance(now)

    def request_manual(self, minutes: int, now: float, requester_user_id: int) -> float:
        if minutes <= 0:
            raise ValueError("minutes must be positive")
        previous_deadline = self._manual_until
        deadline = now + minutes * 60
        self._manual_until = deadline
        try:
            self._sync(now)
        except Exception:
            self._manual_until = previous_deadline
            raise
        self._manual_requesters.add(requester_user_id)
        return deadline

    def advance(self, now: float) -> GuardExpired | None:
        was_active = self._request is not None
        if self._manual_until is not None and now >= self._manual_until:
            self._manual_until = None
        if self._manual_until is None and self._playback_state is PlaybackState.IDLE:
            # Requesters are notified only when the combined guard releases.
            expired_users = tuple(sorted(self._manual_requesters))
            self._manual_requesters.clear()
        else:
            expired_users = ()
        self._sync(now)
        if was_active and self._request is None and expired_users:
            return GuardExpired(expired_users)
        return None

    def close(self) -> None:
        request, self._request = self._request, None
        if request is not None:
            request.close()
            logger.info("Windows system-required power request cleared.")

    def _sync(self, now: float) -> None:
        if self._manual_until is not None and now >= self._manual_until:
            self._manual_until = None
        should_hold = self._playback_state in {PlaybackState.PLAYING, PlaybackState.GRACE_PERIOD} or self._manual_until is not None
        if should_hold and self._request is None:
            self._request = self._request_factory(POWER_REQUEST_REASON)
            logger.info("Windows system-required power request created (display is not inhibited).")
        elif not should_hold and self._request is not None:
            self.close()
