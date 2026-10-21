"""Discord Gateway client and slash command registration."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from .config import AppConfig
from .leases import GuardExpired, LeaseCoordinator
from .notifications import NotificationPreferences

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

    async def notify_guard_expired(self, expiry: GuardExpired, sleep_timeout_description: str | None = None) -> None:
        if not expiry.notification_user_ids:
            return
        sleep_timeout_text = sleep_timeout_description or "The configured Windows sleep timeout could not be read."
        owner_user_id = self.config.discord_owner_user_id
        if not self.notification_preferences.enabled_for(owner_user_id):
            return
        try:
            owner = await self.fetch_user(owner_user_id)
            await owner.send(
                "The Plex Sleep Guard lease has expired. No Plex playback/grace period or manual stay-awake "
                f"timer is active now. {sleep_timeout_text} This is an inactivity timeout; other apps or "
                "system policies may also affect whether Windows sleeps."
            )
        except discord.HTTPException:
            logger.warning("Could not send a guard-expiry DM to configured bot owner %s.", owner_user_id, exc_info=True)

    async def notify_plex_protection(
        self, active: bool, sleep_timeout_description: str | None = None
    ) -> None:
        if active:
            message = (
                "Plex playback was detected. Plex sleep protection is active; this PC may sleep automatically "
                "after playback ends and the configured grace period expires."
            )
        else:
            sleep_timeout_text = (
                sleep_timeout_description or "The configured Windows sleep timeout could not be read."
            )
            message = (
                "Plex playback and its grace period have ended. The Plex sleep-protection reason is cleared; "
                f"a manual stay-awake timer may still keep this PC awake. {sleep_timeout_text} This is an "
                "inactivity timeout; other apps or system policies may also affect whether Windows sleeps."
            )
        owner_user_id = self.config.discord_owner_user_id
        if not self.notification_preferences.enabled_for(owner_user_id):
            return
        try:
            owner = await self.fetch_user(owner_user_id)
            await owner.send(message)
        except discord.HTTPException:
            logger.warning("Could not send a Plex playback DM to configured bot owner %s.", owner_user_id, exc_info=True)
