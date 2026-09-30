"""Deterministic Plex playback and grace-period state machine."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PlaybackState(str, Enum):
    IDLE = "IDLE"
    PLAYING = "PLAYING"
    GRACE_PERIOD = "GRACE_PERIOD"


@dataclass(frozen=True, slots=True)
class StateChange:
    previous: PlaybackState
    current: PlaybackState
    grace_ends_at: float | None


class PlaybackStateMachine:
    """Uses monotonic seconds so local clock changes cannot alter grace timing."""

    def __init__(self, grace_period_seconds: int) -> None:
        if grace_period_seconds < 0:
            raise ValueError("grace_period_seconds must not be negative")
        self.grace_period_seconds = grace_period_seconds
        self.state = PlaybackState.IDLE
        self.grace_ends_at: float | None = None

    def observe_success(self, active: bool, now: float) -> StateChange | None:
        if self.state is PlaybackState.IDLE and active:
            return self._transition(PlaybackState.PLAYING, None)
        if self.state is PlaybackState.PLAYING and not active:
            deadline = now + self.grace_period_seconds
            return self._transition(PlaybackState.GRACE_PERIOD, deadline)
        if self.state is PlaybackState.GRACE_PERIOD and active:
            return self._transition(PlaybackState.PLAYING, None)
        return None

    def advance(self, now: float) -> StateChange | None:
        if self.state is PlaybackState.GRACE_PERIOD and self.grace_ends_at is not None and now >= self.grace_ends_at:
            return self._transition(PlaybackState.IDLE, None)
        return None

    def _transition(self, state: PlaybackState, grace_ends_at: float | None) -> StateChange:
        change = StateChange(self.state, state, grace_ends_at)
        self.state = state
        self.grace_ends_at = grace_ends_at
        return change
