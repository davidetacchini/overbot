import logging
import traceback
from typing import TYPE_CHECKING

import discord
from asyncpg import DataError
from discord import app_commands

import config
from classes.exceptions import (
    NoChoice,
    NotOwner,
    NotPremium,
    OverBotException,
    ProfileLimitReached,
    ProfileNotLinked,
)

if TYPE_CHECKING:
    from bot import OverBot

log = logging.getLogger(__name__)


class OverBotCommandTree(app_commands.CommandTree):
    @staticmethod
    async def _send(interaction: discord.Interaction, *args, **kwargs) -> None:
        if interaction.response.is_done():
            if interaction.is_expired():
                await interaction.channel.send(*args, **kwargs)  # type: ignore
                return
            await interaction.followup.send(*args, ephemeral=True, **kwargs)
        else:
            await interaction.response.send_message(*args, ephemeral=True, **kwargs)

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        bot: OverBot = getattr(interaction, "client")
        command = interaction.command
        original_error = getattr(error, "original", error)

        if command is not None:
            if command._has_any_error_handlers():
                return

        if isinstance(original_error, discord.NotFound):
            return

        if isinstance(error, app_commands.CommandNotFound):
            return

        elif isinstance(error, app_commands.TransformerError):
            await self._send(interaction, str(error))

        elif isinstance(error, app_commands.CheckFailure):
            if isinstance(error, ProfileNotLinked):
                if error.is_author:
                    await self._send(
                        interaction, "You haven't linked a profile yet. Use /profile link to start."
                    )
                else:
                    await self._send(interaction, "This user did not link a profile yet.")

            elif isinstance(error, ProfileLimitReached):
                if error.limit == 5:
                    embed = discord.Embed(color=discord.Color.red())
                    embed.description = (
                        "Maximum limit of profiles reached.\n"
                        f"[Upgrade to Premium]({config.premium}) to be able to link up to 25 profiles."
                    )
                    await self._send(interaction, embed)
                else:
                    await self._send(interaction, "Maximum limit of profiles reached.")

            elif isinstance(error, NotPremium):
                embed = discord.Embed(color=discord.Color.red())
                embed.description = (
                    "This command requires a Premium membership.\n"
                    f"[Click here]({config.premium}) to have a look at the Premium plans."
                )
                await self._send(interaction, embed)

            elif isinstance(error, NotOwner):
                await self._send(interaction, "You are not allowed to run this command.")

            elif isinstance(error, app_commands.NoPrivateMessage):
                await self._send(interaction, "This command cannot be used in direct messages.")

            elif isinstance(error, app_commands.MissingPermissions):
                perms = ", ".join(map(lambda p: f"`{p}`", error.missing_permissions))
                await self._send(
                    interaction, f"You don't have enough permissions to run this command: {perms}"
                )

            elif isinstance(error, app_commands.BotMissingPermissions):
                perms = ", ".join(map(lambda p: f"`{p}`", error.missing_permissions))
                await self._send(
                    interaction, f"I don't have enough permissions to run this command: {perms}"
                )

            elif isinstance(error, app_commands.CommandOnCooldown):
                if command := interaction.command:
                    seconds = round(error.retry_after, 2)
                    await self._send(
                        interaction,
                        f"You can't use `{command.qualified_name}` command for `{seconds}s`.",
                    )

        elif isinstance(error, app_commands.CommandInvokeError):
            original = getattr(error, "original", error)
            if isinstance(original, DataError):
                await self._send(interaction, "The argument you entered cannot be handled.")
            elif isinstance(original, NoChoice):
                pass
            elif isinstance(original, OverBotException):
                await self._send(interaction, str(original))
            else:
                embed = discord.Embed(color=discord.Color.red())
                embed.set_author(
                    name=str(interaction.user), icon_url=interaction.user.display_avatar
                )
                embed.add_field(name="Command", value=interaction.command.qualified_name)  # type: ignore
                if interaction.guild:
                    guild = f"{str(interaction.guild)} ({interaction.guild_id})"
                    embed.add_field(name="Guild", value=guild, inline=False)
                try:
                    exc = "".join(
                        traceback.format_exception(
                            type(original),
                            original,
                            original.__traceback__,
                            chain=False,
                        )
                    )
                except AttributeError:
                    exc = f"{type(original)}\n{original}"
                embed.description = f"```py\n{exc}\n```"
                embed.timestamp = interaction.created_at
                if not bot.debug:
                    await bot.webhook.send(embed=embed)
                else:
                    log.exception(original.__traceback__)
                await self._send(
                    interaction,
                    "This command ran into an error. The incident has been reported and will be fixed as soon as possible.",
                )
