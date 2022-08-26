from __future__ import annotations

import secrets

from typing import TYPE_CHECKING, Any, Literal, get_args

import discord

from discord import app_commands
from discord.ext import commands

from utils.funcs import hero_autocomplete
from classes.profile import ROLES

if TYPE_CHECKING:
    from bot import OverBot

HeroCategories = Literal["damage", "support", "tank"]
MemeCategories = Literal["hot", "new", "top", "rising"]
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

    def _get_random_map(self, category: None | str) -> str:
        maps = self.bot.maps
        if not category:
            map_ = secrets.choice(maps)
        else:
            categorized_maps = [m for m in maps if category in m["types"]]
            map_ = secrets.choice(categorized_maps)
        return map_["name"]

    async def _get_random_meme(self, category: str) -> dict[str, Any]:
        url = f"https://www.reddit.com/r/Overwatch_Memes/{category}.json"
        async with self.bot.session.get(url) as r:
            memes = await r.json()
        # excluding .mp4 and files from other domains
        memes = [
            meme
            for meme in memes["data"]["children"]
            if not meme["data"]["secure_media"] or not meme["data"]["is_reddit_media_domain"]
        ]
        return secrets.choice(memes)

    def _embed_meme(self, interaction: discord.Interaction, meme: dict[str, Any]) -> discord.Embed:
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.title = meme["data"]["title"]
        upvotes, comments = meme["data"]["ups"], meme["data"]["num_comments"]
        embed.description = f"{upvotes} upvotes - {comments} comments"
        embed.url = f'https://reddit.com{meme["data"]["permalink"]}'
        embed.set_image(url=meme["data"]["url"])
        embed.set_footer(text=meme["data"]["subreddit_name_prefixed"])
        return embed

    @app_commands.command()
    @app_commands.autocomplete(hero=hero_autocomplete)
    @app_commands.describe(hero="The hero you want detail for")
    async def detail(self, interaction: discord.Interaction, hero: str):
        "Returns details about a hero"
        await interaction.response.defer(thinking=True)
        sel = self.bot.heroes[hero]
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.set_author(
            name=hero.capitalize(), icon_url=self.bot.config.hero_portrait_url.format(hero)
        )
        embed.description = sel["description"]

        embed.add_field(name="Role", value=f"{ROLES.get(sel['role'].lower())} {sel['role']}")
        difficulty = [":star:" for _ in range(sel["difficulty"])]
        embed.add_field(name="Difficulty", value=" ".join(difficulty))

        weapons = ""
        for name, description in sel["weapons"]:
            weapons += f"`{name}`: {description}\n"
        embed.add_field(name="Weapons", value=weapons, inline=False)

        abilities = ""
        for name, description in sel["abilities"]:
            abilities += f"`{name}`: {description}\n"
        embed.add_field(name="Abilities", value=abilities)

        try:
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(e)

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
    @app_commands.describe(category="The category to get a random map from")
    async def maptoplay(
        self, interaction: discord.Interaction, category: MapCategories = None
    ) -> None:
        """Returns a random map"""
        map_ = self._get_random_map(category)
        await interaction.response.send_message(map_)

    @app_commands.command()
    @app_commands.describe(category="The category to get a random meme from")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: i.user.id)
    async def meme(self, interaction: discord.Interaction, category: MemeCategories = None) -> None:
        """Returns a random Overwatch meme"""
        categories = tuple(get_args(MemeCategories))
        category = category or secrets.choice(categories)
        meme = await self._get_random_meme(str(category))
        embed = self._embed_meme(interaction, meme)
        await interaction.response.send_message(embed=embed)


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Fun(bot))
