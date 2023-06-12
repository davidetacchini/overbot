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
    "control",
    "assault",
    "escort",
    "capture the flag",
    "hybrid",
    "elimination",
    "deathmatch",
    "team deathmatch",
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
    async def roletoplay(self, interaction: discord.Interaction) -> None:
        """Returns a random role"""
        roles = ("Tank", "Damage", "Support", "Flex")
        await interaction.response.send_message(secrets.choice(roles))

    @app_commands.command()
    async def meme(self, interaction: discord.Interaction) -> None:
        """Returns a random Overwatch meme"""
        await interaction.response.send_message(
            "Due to Reddit's new APIs policy, this command is no longer available. Thanks for the understanding."
        )


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Fun(bot))
