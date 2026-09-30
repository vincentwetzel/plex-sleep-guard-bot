"""Application entry point and shutdown cleanup."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time

from .config import AppConfig
from .discord_bot import SleepGuardBot
from .leases import GuardExpired, LeaseCoordinator
from .logging_setup import configure_logging
from .notifications import NotificationPreferences
from .plex import PlexMonitor
from .playback import PlaybackStateMachine
from .power_windows import WindowsPowerRequest
from .service import lease_expiry_loop, plex_poll_loop

logger = logging.getLogger(__name__)


async def run(config: AppConfig) -> None:
    monitor = PlexMonitor(config.plex_server_url, config.plex_token)
    state = PlaybackStateMachine(config.plex_grace_period_minutes * 60)
    leases = LeaseCoordinator(WindowsPowerRequest)
    notification_preferences = NotificationPreferences(
        config.project_dir / "state" / "guard_notification_preferences.json"
    )
    state_label = "IDLE"
    last_log = 0.0

    def set_state(label: str) -> None:
        nonlocal state_label
        state_label = label

    async def periodic_status() -> None:
        nonlocal last_log
        while True:
            await asyncio.sleep(60)
            if leases.request_active and time.monotonic() - last_log >= 60:
                logger.info("Power lease status: state=%s; one system-required request active.", state_label)
                try:
                    process = await asyncio.create_subprocess_exec(
                        "powercfg",
                        "/requests",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                    output, _ = await asyncio.wait_for(process.communicate(), timeout=10)
                    if process.returncode == 0:
                        logger.info("powercfg /requests snapshot while protected:\n%s", output.decode(errors="replace").strip())
                    else:
                        logger.warning("powercfg /requests exited with code %s.", process.returncode)
                except (OSError, asyncio.TimeoutError) as exc:
                    logger.warning("Could not capture powercfg /requests: %s", exc)
                last_log = time.monotonic()

    async def supervisor_control_loop() -> None:
        stop_marker = config.project_dir / "run" / "stop.request"
        restart_marker = config.project_dir / "run" / "restart.request"
        while True:
            if stop_marker.exists():
                logger.info("Supervisor requested a graceful stop.")
                await bot.close()
                return
            if restart_marker.exists():
                logger.info("Supervisor requested a graceful restart.")
                await bot.close()
                return
            await asyncio.sleep(1)

    bot = SleepGuardBot(config, leases, notification_preferences)

    async def notify_guard_expired(expiry: GuardExpired) -> None:
        await bot.notify_guard_expired(expiry)

    tasks: list[asyncio.Task[None]] = []
    try:
        await monitor.start()
        tasks.append(
            asyncio.create_task(
                plex_poll_loop(
                    monitor,
                    state,
                    leases,
                    config.plex_poll_interval_seconds,
                    set_state,
                    notify_guard_expired,
                ),
                name="plex-poll-loop",
            )
        )
        tasks.append(
            asyncio.create_task(
                lease_expiry_loop(state, leases, set_state, notify_guard_expired), name="lease-expiry-loop"
            )
        )
        tasks.append(asyncio.create_task(periodic_status(), name="status-log-loop"))
        if config.supervised:
            tasks.append(asyncio.create_task(supervisor_control_loop(), name="supervisor-control-loop"))
        await bot.start(config.discord_bot_token)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            leases.close()
        finally:
            try:
                await monitor.close()
            finally:
                await bot.close()


def main() -> None:
    try:
        config = AppConfig.load()
        configure_logging(config.log_dir)
        if os.name != "nt":
            raise OSError("Plex Sleep Guard Bot requires Windows for power request support.")
        asyncio.run(run(config))
    except KeyboardInterrupt:
        logger.info("Shutdown requested by keyboard interrupt.")
    except (OSError, ValueError) as exc:
        logging.basicConfig(level=logging.ERROR)
        logger.error("Startup or runtime failure: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
