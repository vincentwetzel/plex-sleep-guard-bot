"""Discord Gateway client and slash command registration."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands

from .config import AppConfig
from .leases import GuardExpired, LeaseCoordinator
from .notifications import NotificationPreferences
from .power_windows import SleepTimeoutInfo

logger = logging.getLogger(__name__)


class SleepGuardBot(commands.Bot):
    def __init__(
        self,
        config: AppConfig,
        leases: LeaseCoordinator,
        notification_preferences: NotificationPreferences,
    ) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            application_id=config.discord_application_id,
        )
        self.config = config
        self.leases = leases
        self.notification_preferences = notification_preferences

        @self.tree.command(name="stay-awake", description="Keep this PC awake for a bounded number of minutes.")
        @app_commands.describe(minutes="How many minutes to keep the PC awake")
        async def stay_awake(interaction: discord.Interaction, minutes: int) -> None:
            if not 1 <= minutes <= self.config.stay_awake_max_minutes:
                await interaction.response.send_message(
                    f"Choose a whole number from 1 to {self.config.stay_awake_max_minutes} minutes.",
                    ephemeral=True,
                )
                return
            await interaction.response.defer(ephemeral=True)
            try:
                now = time.monotonic()
                old_expiry = self.leases.advance(now)
                if old_expiry is not None:
                    await self.notify_guard_expired(old_expiry)
                expires_at = self.leases.request_manual(minutes, now, interaction.user.id)
            except OSError:
                logger.exception("Could not create the Windows power request for a Discord command.")
                await interaction.followup.send(
                    "Windows could not update the stay-awake request. Check the bot log.", ephemeral=True
                )
                return
            # Use wall time only for the human-facing estimate; expiry itself uses monotonic time.
            expiry_epoch = time.time() + max(0, expires_at - time.monotonic())
            expiry = datetime.fromtimestamp(expiry_epoch, tz=timezone.utc)
            await interaction.followup.send(
                f"This PC will stay awake for up to {minutes} minutes (until about {discord.utils.format_dt(expiry, style='t')}).",
                ephemeral=True,
            )

        @self.tree.command(
            name="guard-notifications",
            description="Choose whether the configured bot owner receives guard status DMs.",
        )
        @app_commands.describe(enabled="Send the configured owner Plex and guard-expiry DMs")
        async def guard_notifications(interaction: discord.Interaction, enabled: bool) -> None:
            if interaction.user.id != self.config.discord_owner_user_id:
                await interaction.response.send_message(
                    "Only the configured bot owner can change guard notification settings.", ephemeral=True
                )
                return
            try:
                self.notification_preferences.set_enabled(self.config.discord_owner_user_id, enabled)
            except OSError:
                logger.exception("Could not save a user's guard notification preference.")
                await interaction.response.send_message(
                    "I couldn't save that preference. Check that the project folder is writable.", ephemeral=True
                )
                return
            status = "on" if enabled else "off"
            await interaction.response.send_message(
                f"Guard status DMs to the configured owner are now **{status}**.", ephemeral=True
            )

    async def setup_hook(self) -> None:
        synced = await self.tree.sync()
        logger.info("Synced %d global application command(s).", len(synced))

    async def on_ready(self) -> None:
        logger.info("Connected to Discord as %s (application ID %s).", self.user, self.config.discord_application_id)

    async def notify_guard_expired(self, expiry: GuardExpired, sleep_timeout: SleepTimeoutInfo | None = None) -> None:
        if not expiry.notification_user_ids:
            return
        sleep_timeout_text = self._sleep_timing(sleep_timeout)
        owner_user_id = self.config.discord_owner_user_id
        if not self.notification_preferences.enabled_for(owner_user_id):
            return
        try:
            owner = await self.fetch_user(owner_user_id)
            await owner.send(
                f"Guard ended. PC is unprotected. {sleep_timeout_text}"
            )
        except discord.HTTPException:
            logger.warning("Could not send a guard-expiry DM to configured bot owner %s.", owner_user_id, exc_info=True)

    async def notify_plex_protection(
        self,
        active: bool,
        grace_period_minutes: int,
        sleep_timeout: SleepTimeoutInfo | None = None,
    ) -> None:
        if active:
            message = f"Plex active. PC protected; {grace_period_minutes} min grace after playback ends."
        else:
            message = f"Plex grace ended. A manual timer may still protect the PC. {self._sleep_timing(sleep_timeout)}"
        owner_user_id = self.config.discord_owner_user_id
        if not self.notification_preferences.enabled_for(owner_user_id):
            return
        try:
            owner = await self.fetch_user(owner_user_id)
            await owner.send(message)
        except discord.HTTPException:
            logger.warning("Could not send a Plex playback DM to configured bot owner %s.", owner_user_id, exc_info=True)

    @staticmethod
    def _sleep_timing(sleep_timeout: SleepTimeoutInfo | None) -> str:
        if sleep_timeout is None:
            return "Windows sleep timeout unavailable."

        if sleep_timeout.on_ac_power is None:
            return (
                f"Sleep timeout: AC {sleep_timeout.ac_seconds // 60} min; "
                f"battery {sleep_timeout.dc_seconds // 60} min."
            )

        source = "AC" if sleep_timeout.on_ac_power else "battery"
        seconds = sleep_timeout.ac_seconds if sleep_timeout.on_ac_power else sleep_timeout.dc_seconds
        if seconds == 0:
            return f"Sleep timeout: never on {source}."

        minutes = (seconds + 59) // 60
        target = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        return (
            f"Sleep timeout: {minutes} min on {source} "
            f"(about {discord.utils.format_dt(target, style='t')} if idle from now)."
        )
