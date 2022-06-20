from __future__ import annotations

import secrets

from typing import TYPE_CHECKING, Literal

import discord

from discord import app_commands
from discord.ext import commands

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
    def __init__(self, bot: OverBot):
        self.bot = bot

    def get_random_hero(self, category: str) -> str:
        heroes = list(self.bot.heroes.values())
        if not category:
            hero = secrets.choice(heroes)
        else:
            categorized_heroes = [h for h in heroes if h["role"] == category]
            hero = secrets.choice(categorized_heroes)
        return hero["name"]

    def get_random_map(self, category: str) -> str:
        maps = self.bot.maps
        if not category:
            map_ = secrets.choice(maps)
        else:
            categorized_maps = [m for m in maps if category in m["types"]]
            map_ = secrets.choice(categorized_maps)
        return map_["name"]

    async def get_meme(self, category: str) -> dict:
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

    def embed_meme(self, interaction: discord.Interaction, meme: dict) -> discord.Embed:
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.title = meme["data"]["title"]
        upvotes, comments = meme["data"]["ups"], meme["data"]["num_comments"]
        embed.description = f"{upvotes} upvotes - {comments} comments"
        embed.url = f'https://reddit.com{meme["data"]["permalink"]}'
        embed.set_image(url=meme["data"]["url"])
        embed.set_footer(text=meme["data"]["subreddit_name_prefixed"])
        return embed

    @app_commands.command()
    @app_commands.describe(category="The category to get a random hero from")
    async def herotoplay(self, interaction: discord.Interaction, category: HeroCategories = None):
        """Returns a random hero"""
        hero = self.get_random_hero(category)
        await interaction.response.send_message(hero)

    @app_commands.command()
    async def roletoplay(self, interaction: discord.Interaction):
        """Returns a random role"""
        roles = ("Tank", "Damage", "Support", "Flex")
        await interaction.response.send_message(secrets.choice(roles))

    @app_commands.command()
    @app_commands.describe(category="The category to get a random map from")
    async def maptoplay(self, interaction: discord.Interaction, *, category: MapCategories = None):
        """Returns a random map"""
        map_ = self.get_random_map(category)
        await interaction.response.send_message(map_)

    # TODO: if no category then select a random one
    @app_commands.command()
    @app_commands.describe(category="The category to get a random meme from")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def meme(self, interaction: discord.Interaction, category: MemeCategories = None):
        """Returns a random Overwatch meme"""
        category = category or secrets.choice(("hot", "new", "top", "rising"))
        meme = await self.get_meme(category)
        embed = self.embed_meme(interaction, meme)
        await interaction.response.send_message(embed=embed)


async def setup(bot: OverBot):
    await bot.add_cog(Fun(bot))
