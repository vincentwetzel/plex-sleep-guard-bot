"""Plex polling and independent lease-expiry loops."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from .leases import GuardExpired, LeaseCoordinator
from .plex import PlexMonitor
from .playback import PlaybackStateMachine

logger = logging.getLogger(__name__)


async def plex_poll_loop(
    monitor: PlexMonitor,
    state: PlaybackStateMachine,
    leases: LeaseCoordinator,
    poll_interval_seconds: int,
    on_state: Callable[[str], None],
    on_guard_expired: Callable[[GuardExpired], Awaitable[None]],
) -> None:
    last_successful_poll: datetime | None = None
    while True:
        started = time.monotonic()
        result = await monitor.poll()
        if result.succeeded:
            last_successful_poll = datetime.now(timezone.utc)
            change = state.observe_success(result.has_active_sessions, time.monotonic())
            if change is not None:
                logger.info("Plex state changed: %s -> %s", change.previous.value, change.current.value)
                on_state(change.current.value)
            try:
                expiry = leases.set_playback_state(state.state, time.monotonic())
                if expiry is not None:
                    await on_guard_expired(expiry)
            except OSError:
                # Keep playback state and retry synchronization from the expiry loop.
                logger.exception("Could not synchronize the Windows power request; it will be retried.")
            logger.info(
                "Plex poll succeeded: %d active session(s); state=%s; last success=%s",
                len(result.sessions),
                state.state.value,
                last_successful_poll.isoformat(),
            )
        else:
            # Deliberately leave both state and Plex lease unchanged on failed polls.
            last_success_text = last_successful_poll.isoformat() if last_successful_poll else "never"
            logger.warning(
                "Plex poll failed; preserving state=%s; last successful poll=%s",
                state.state.value,
                last_success_text,
            )
        elapsed = time.monotonic() - started
        if elapsed > poll_interval_seconds * 2:
            logger.warning("Plex monitor loop took %.1fs (configured interval %ss).", elapsed, poll_interval_seconds)
        await asyncio.sleep(max(0, poll_interval_seconds - elapsed))


async def lease_expiry_loop(
    state: PlaybackStateMachine,
    leases: LeaseCoordinator,
    on_state: Callable[[str], None],
    on_guard_expired: Callable[[GuardExpired], Awaitable[None]],
) -> None:
    while True:
        now = time.monotonic()
        change = state.advance(now)
        if change is not None:
            logger.info("Plex grace period ended: %s -> %s", change.previous.value, change.current.value)
            on_state(change.current.value)
        try:
            expiry = leases.set_playback_state(state.state, now)
            if expiry is not None:
                await on_guard_expired(expiry)
        except OSError:
            logger.exception("Could not synchronize the Windows power request; retrying shortly.")
        await asyncio.sleep(1)
