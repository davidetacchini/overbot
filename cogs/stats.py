from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from discord import app_commands
from discord.ext import commands
from discord.app_commands import Choice

from utils.funcs import platform_choices, hero_autocomplete
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
        platform: None | str = None,
        username: None | str = None,
        *,
        profile: None | Profile = None,
    ) -> None:
        profile = profile or Profile(platform, username, interaction=interaction)
        await profile.compute_data()
        if profile.is_private():
            embed: discord.Embed | list[discord.Embed] = profile.embed_private()
        else:
            embed = profile.embed_stats(hero)
        await self.bot.paginate(embed, interaction=interaction)

    @app_commands.command()
    @app_commands.choices(platform=platform_choices)
    @app_commands.describe(platform="The username of the player")
    @app_commands.describe(username="The platform of the player")
    async def ratings(
        self, interaction: discord.Interaction, platform: Choice[str], *, username: str
    ) -> None:
        """Provides player ratings."""
        await interaction.response.defer(thinking=True)
        profile = Profile(platform.value, username, interaction=interaction)
        await profile.compute_data()
        if profile.is_private():
            embed = profile.embed_private()
        else:
            embed = await profile.embed_ratings()
        await interaction.followup.send(embed=embed)

    @app_commands.command()
    @app_commands.choices(platform=platform_choices)
    @app_commands.describe(platform="The username of the player")
    @app_commands.describe(username="The platform of the player")
    async def stats(
        self, interaction: discord.Interaction, platform: Choice[str], *, username: str
    ) -> None:
        """Provides player general stats."""
        await interaction.response.defer(thinking=True)
        await self.show_stats_for(interaction, "allHeroes", platform.value, username)

    @app_commands.command()
    @app_commands.autocomplete(hero=hero_autocomplete)
    @app_commands.choices(platform=platform_choices)
    @app_commands.describe(hero="The hero name to see the stats for")
    @app_commands.describe(platform="The username of the player")
    @app_commands.describe(username="The platform of the player")
    async def hero(
        self,
        interaction: discord.Interaction,
        hero: str,
        platform: Choice[str],
        *,
        username: str,
    ) -> None:
        """Provides player general stats for a given hero."""
        await interaction.response.defer(thinking=True)
        await self.show_stats_for(interaction, hero, platform.value, username)

    @app_commands.command()
    @app_commands.choices(platform=platform_choices)
    @app_commands.describe(platform="The username of the player")
    @app_commands.describe(username="The platform of the player")
    async def summary(
        self, interaction: discord.Interaction, platform: Choice[str], *, username: str
    ) -> None:
        """Provides player summarized stats."""
        await interaction.response.defer(thinking=True)
        profile = Profile(platform.value, username, interaction=interaction)
        await profile.compute_data()
        if profile.is_private():
            embed = profile.embed_private()
        else:
            embed = profile.embed_summary()
        await interaction.followup.send(embed=embed)


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Stats(bot))
