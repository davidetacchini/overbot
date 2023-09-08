import logging
import traceback

import discord

from asyncpg import DataError
from discord import app_commands

from classes.exceptions import (
    NoChoice,
    NotOwner,
    NotPremium,
    OverBotException,
    ProfileNotLinked,
    ProfileLimitReached,
)

log = logging.getLogger("overbot")


class OverBotCommandTree(app_commands.CommandTree):
    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        bot = interaction.client
        command = interaction.command
        original_error = getattr(error, "original", error)

        if command is not None:
            if command._has_any_error_handlers():
                return

        if isinstance(original_error, discord.NotFound):
            return

        async def send(payload: str | discord.Embed, ephemeral: bool = True) -> None:
            if isinstance(payload, str):
                kwargs = {"content": payload}
            elif isinstance(payload, discord.Embed):
                kwargs = {"embed": payload}

            if interaction.response.is_done():
                await interaction.followup.send(**kwargs, ephemeral=ephemeral)
            else:
                await interaction.response.send_message(**kwargs, ephemeral=ephemeral)

        if isinstance(error, app_commands.CommandNotFound):
            return

        elif isinstance(error, app_commands.TransformerError):
            await send(str(error))

        elif isinstance(error, app_commands.CheckFailure):
            if isinstance(error, ProfileNotLinked):
                if error.is_author:
                    await send("You haven't linked a profile yet. Use /profile link to start.")
                else:
                    await send("This user did not link a profile yet.")

            elif isinstance(error, ProfileLimitReached):
                if error.limit == 5:
                    premium = bot.config.premium
                    embed = discord.Embed(color=discord.Color.red())
                    embed.description = (
                        "Maximum limit of profiles reached.\n"
                        f"[Upgrade to Premium]({premium}) to be able to link up to 25 profiles."
                    )
                    await send(embed)
                else:
                    await send("Maximum limit of profiles reached.")

            elif isinstance(error, NotPremium):
                premium = bot.config.premium
                embed = discord.Embed(color=discord.Color.red())
                embed.description = (
                    "This command requires a Premium membership.\n"
                    f"[Click here]({premium}) to have a look at the Premium plans."
                )
                await send(embed)

            elif isinstance(error, NotOwner):
                await send("You are not allowed to run this command.")

            elif isinstance(error, app_commands.NoPrivateMessage):
                await send("This command cannot be used in direct messages.")

            elif isinstance(error, app_commands.MissingPermissions):
                perms = ", ".join(map(lambda p: f"`{p}`", error.missing_permissions))
                await send(f"You don't have enough permissions to run this command: {perms}")

            elif isinstance(error, app_commands.BotMissingPermissions):
                perms = ", ".join(map(lambda p: f"`{p}`", error.missing_permissions))
                await send(f"I don't have enough permissions to run this command: {perms}")

            elif isinstance(error, app_commands.CommandOnCooldown):
                command = interaction.command.qualified_name
                seconds = round(error.retry_after, 2)
                await send(f"You can't use `{command}` command for `{seconds}s`.")

        elif isinstance(error, app_commands.CommandInvokeError):
            original = getattr(error, "original", error)
            if isinstance(original, DataError):
                await send("The argument you entered cannot be handled.")
            elif isinstance(original, NoChoice):
                pass
            elif isinstance(original, OverBotException):
                await send(str(original))
            else:
                embed = discord.Embed(color=discord.Color.red())
                embed.set_author(
                    name=str(interaction.user), icon_url=interaction.user.display_avatar
                )
                embed.add_field(name="Command", value=interaction.command.qualified_name)
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
                await send(
                    "This command ran into an error. The incident has been reported and will be fixed as soon as possible."
                )
