from __future__ import annotations

import secrets

from typing import TYPE_CHECKING, Literal

import discord

from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot import OverBot

HeroCategories = Literal["damage", "support", "tank"]
MapCategories = Literal[
    "assault",
    "capture-the-flag",
    "control",
    "deathmatch",
    "elimination",
    "escort",
    "hybrid",
    "push",
    "team-deathmatch",
]


class Fun(commands.Cog):
    def __init__(self, bot: OverBot) -> None:
        self.bot = bot

    def _get_random_hero(self, category: None | str) -> str:
        heroes = list(self.bot.heroes.values())
        if not category:
            hero = secrets.choice(heroes)
        else:
            categorized_heroes = [h for h in heroes if h["role"] == category]
            hero = secrets.choice(categorized_heroes)
        return hero["name"]

    def _get_random_map(self, category: None | str) -> str:
        maps = list(self.bot.maps.values())
        if not category:
            map_ = secrets.choice(maps)
        else:
            categorized_maps = [m for m in maps if category in m["gamemodes"]]
            map_ = secrets.choice(categorized_maps)
        return map_["name"]

    @app_commands.command()
    @app_commands.describe(category="The category to get a random hero from")
    async def herotoplay(
        self, interaction: discord.Interaction, category: HeroCategories = None
    ) -> None:
        """Returns a random hero"""
        hero = self._get_random_hero(category)
        await interaction.response.send_message(hero)

    @app_commands.command()
    @app_commands.describe(category="The category to get a random hero from")
    async def goldengun(
        self, interaction: discord.Interaction, category: HeroCategories = None
    ) -> None:
        """Returns a hero to get a golden gun for"""
        hero = self._get_random_hero(category)
        await interaction.response.send_message(hero)

    @app_commands.command()
    @app_commands.describe(category="The category to get a random map from")
    async def maptoplay(
        self, interaction: discord.Interaction, category: MapCategories = None
    ) -> None:
        """Returns a random map"""
        map_ = self._get_random_map(category)
        await interaction.response.send_message(map_)

    @app_commands.command()
    async def roletoplay(self, interaction: discord.Interaction) -> None:
        """Returns a random role"""
        roles = ("Tank", "Damage", "Support", "Flex")
        await interaction.response.send_message(secrets.choice(roles))


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Fun(bot))
