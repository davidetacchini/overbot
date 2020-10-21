import secrets

import discord
from discord.ext import commands

from utils.globals import command_embed, embed_exception

ROLES = [
    {
        "name": "tank",
        "icon": "https://cdn.discordapp.com/attachments/531857697625341952/550347529225764865/TankIcon.png",
        "color": 0xFAA528,
    },
    {
        "name": "damage",
        "icon": "https://cdn.discordapp.com/attachments/531857697625341952/550347576210227211/OffenseIcon.png",
        "color": 0xE61B23,
    },
    {
        "name": "support",
        "icon": "https://cdn.discordapp.com/attachments/531857697625341952/550347552575324160/SupportIcon.png",
        "color": 0x13A549,
    },
    {
        "name": "flex",
        "icon": "https://cdn.discordapp.com/attachments/580361889985593345/637232674062467092/FlexIcon.png",
        "color": 0xFA9C1E,
    },
]


class Randoms(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_hero(self):
        url = "https://overwatch-api.tekrop.fr/heroes"
        async with self.bot.session.get(url) as r:
            return secrets.choice(await r.json())

    @staticmethod
    def get_hero_color(hero):
        if hero["role"] == "tank":
            return 0xFAA528
        elif hero["role"] == "damage":
            return 0xE61B23
        return 0x13A549

    async def embed_random_hero(self):
        hero = await self.get_hero()

        embed = discord.Embed(color=self.get_hero_color(hero))
        embed.title = hero["name"].upper()
        embed.set_thumbnail(url=hero["portrait"])

        for role in ROLES:
            if role["name"] == hero["role"]:
                icon = role["icon"]

        embed.set_footer(
            text=hero["role"].capitalize(),
            icon_url=icon,
        )
        return embed

    def random_role(self):
        rand = secrets.choice(ROLES)
        embed = discord.Embed(color=rand["color"])
        embed.title = str(rand["name"]).upper()
        embed.set_thumbnail(url=rand["icon"])
        return embed

    @commands.group(invoke_without_command=True)
    async def random(self, ctx, command: str = None):
        """Returns a random hero or role, based on your choice.

        Choices
            - Hero: random hero
            - Role: random role
        """
        embed = command_embed(ctx, self.bot.get_command(ctx.command.name))
        await ctx.send(embed=embed)

    @random.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def hero(self, ctx):
        """Returns a random hero to play."""
        try:
            embed = await self.embed_random_hero()
        except Exception as exc:
            await ctx.send(embed=embed_exception(exc))
        else:
            await ctx.send(embed=embed)

    @random.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def role(self, ctx):
        """Returns a random role to play."""
        try:
            embed = self.random_role()
        except Exception as exc:
            await ctx.send(embed=embed_exception(exc))
        else:
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Randoms(bot))
