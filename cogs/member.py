from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from discord import Color, ui, app_commands
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
    async def premium(self, interaction: discord.Interaction) -> None:
        """Shows your premium status"""
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.title = "Premium Status"

        member = "Premium" if interaction.user.id in self.bot.premiums else "N/A"
        guild = "Premium" if interaction.guild_id in self.bot.premiums else "N/A"

        embed.description = f"Your Status: `{member}`\nServer Status: `{guild}`"

        view = ui.View()
        view.add_item(ui.Button(label="Premium", url=self.bot.config.premium))

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(extras=dict(premium=True))
    @app_commands.describe(
        color="An HEX or RGB color. E.g. #218ffe or 33,143,254. Leave blank to reset"
    )
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
                await interaction.response.send_message(
                    "Color already set to default.", ephemeral=True
                )
                return
            else:
                await interaction.response.send_message("Color successfully reset.", ephemeral=True)
                return

        embed = discord.Embed(color=color)
        query = "UPDATE member SET embed_color = $1 WHERE id = $2;"
        await self.bot.pool.execute(query, color, interaction.user.id)
        self.bot.embed_colors[interaction.user.id] = color
        embed.description = "Color successfully set."
        await interaction.response.send_message(embed=embed)


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Member(bot))
