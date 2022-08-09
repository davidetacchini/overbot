from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from discord import Color, app_commands
from discord.ext import commands

from utils.checks import is_premium
from classes.exceptions import InvalidColor

if TYPE_CHECKING:
    from bot import OverBot


class ColorTransformer(app_commands.Transformer):
    @classmethod
    async def transform(cls, interaction: discord.Interaction, value: str) -> discord.Color:
        if len(value.split(",")) == 3:
            r, g, b = value.split(",")
            value = f"rgb({r}, {g}, {b})"
        try:
            color = Color.from_str(value)
        except ValueError:
            raise InvalidColor() from None
        else:
            return color


class Member(commands.Cog):
    def __init__(self, bot: OverBot) -> None:
        self.bot = bot

    @app_commands.command()
    @app_commands.guild_only()
    async def premium(self, interaction: discord.Interaction) -> None:
        """Shows your premium status"""
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.title = "Premium Status"

        member = "Active" if interaction.user.id in self.bot.premiums else "N/A"
        guild = "Active" if interaction.guild_id in self.bot.premiums else "N/A"

        description = f"Your Status: `{member}`\nServer Status: `{guild}`"

        to_check = (member, guild)
        if all(x == "N/A" for x in to_check):
            link = "[Upgrade to Premium]({premium})".format(premium=self.bot.config.premium)
            description = description + "\n" + link

        embed.description = description
        await interaction.response.send_message(embed=embed)

    @app_commands.command(extras=dict(premium=True))
    @app_commands.describe(color="The color to use for the embeds. Leave blank to reset")
    @is_premium()
    async def color(
        self,
        interaction: discord.Interaction,
        *,
        color: app_commands.Transform[str, ColorTransformer] = None,
    ) -> None:
        """Set a custom color for the embeds"""
        if color is None:
            query = "UPDATE member SET embed_color = NULL WHERE id = $1;"
            await self.bot.pool.execute(query, interaction.user.id)
            try:
                del self.bot.embed_colors[interaction.user.id]
            except KeyError:
                return await interaction.response.send_message(
                    "Color already set to default.", ephemeral=True
                )
            else:
                return await interaction.response.send_message(
                    "Color successfully reset.", ephemeral=True
                )

        embed = discord.Embed(color=color)
        query = "UPDATE member SET embed_color = $1 WHERE id = $2;"
        await self.bot.pool.execute(query, color, interaction.user.id)
        self.bot.embed_colors[interaction.user.id] = color
        embed.description = "Color successfully set."
        await interaction.response.send_message(embed=embed)


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Member(bot))
