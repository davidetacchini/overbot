from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from discord import app_commands
from discord.ext import commands

from classes.ui import PlatformSelectMenu
from utils.helpers import hero_autocomplete
from classes.profile import Profile

if TYPE_CHECKING:
    from bot import OverBot


class Stats(commands.Cog):
    def __init__(self, bot: OverBot) -> None:
        self.bot = bot

    async def show_stats_for(
        self,
        interaction: discord.Interaction,
        hero: str,
        battletag: None | str = None,
        *,
        profile: None | Profile = None,
    ) -> None:
        profile = profile or Profile(battletag, interaction=interaction)
        await profile.fetch_data()

        if profile.is_private():
            embed = profile.embed_private()
            await interaction.followup.send(embed=embed)
            return

        data = profile.embed_stats(hero)
        value = "console" if not data["pc"] else "pc"
        view = PlatformSelectMenu(data[value], interaction=interaction)
        view.add_platforms(data)
        await view.start()

    @app_commands.command()
    @app_commands.describe(battletag="The battletag of the player")
    async def ratings(self, interaction: discord.Interaction, *, battletag: str) -> None:
        """Provides ratings for a player"""
        await interaction.response.defer(thinking=True)
        profile = Profile(battletag, interaction=interaction)
        await profile.fetch_data()

        if profile.is_private():
            embed = profile.embed_private()
            await interaction.followup.send(embed=embed)
            return

        data = profile.embed_ratings()
        value = "console" if not data["pc"] else "pc"
        view = PlatformSelectMenu(data[value], interaction=interaction)
        view.add_platforms(data)
        await view.start()

    @app_commands.command()
    @app_commands.autocomplete(hero=hero_autocomplete)
    @app_commands.describe(battletag="The battletag of the player")
    @app_commands.describe(
        hero="The hero name to see the stats for. If not given then it shows general stats"
    )
    async def stats(
        self, interaction: discord.Interaction, *, battletag: str, hero: str = "all-heroes"
    ) -> None:
        """Provides general stats or hero specific stats for a player"""
        await interaction.response.defer(thinking=True)
        await self.show_stats_for(interaction, hero, battletag)

    @app_commands.command()
    @app_commands.describe(battletag="The battletag of the player")
    async def summary(self, interaction: discord.Interaction, *, battletag: str) -> None:
        """Provides summarized stats for a player

        Data from both competitive and quickplay, and/or pc and console is merged
        """
        await interaction.response.defer(thinking=True)
        profile = Profile(battletag, interaction=interaction)
        await profile.fetch_data()
        if profile.is_private():
            embed = profile.embed_private()
        else:
            embed = await profile.embed_summary()
        await interaction.followup.send(embed=embed)


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Stats(bot))
