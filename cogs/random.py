import secrets

import discord
from discord.ext import commands

from classes.converters import MapCategory, HeroCategory

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


class Random(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get(self, url):
        async with self.bot.session.get(url) as r:
            return await r.json()

    @staticmethod
    def get_hero_color(hero):
        if hero["role"] == "tank":
            return 0xFAA528
        elif hero["role"] == "damage":
            return 0xE61B23
        return 0x13A549

    @staticmethod
    def get_by_category(items, path, category):
        return [i for i in items if i[path] == category]

    async def random_hero(self, category):
        heroes = await self.get(self.bot.config.random["hero"])

        if not category:
            hero = secrets.choice(heroes)
        else:
            categorized_heroes = self.get_by_category(heroes, "role", category)
            hero = secrets.choice(categorized_heroes)

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

    @staticmethod
    def random_role():
        rand = secrets.choice(ROLES)
        embed = discord.Embed(color=rand["color"])
        embed.title = str(rand["name"]).upper()
        embed.set_thumbnail(url=rand["icon"])
        return embed

    async def random_map(self, category):
        maps = await self.get(self.bot.config.random["map"])

        if not category:
            _map = secrets.choice(maps)
        else:
            categorized_maps = self.get_by_category(maps, "type", category)
            _map = secrets.choice(categorized_maps)

        embed = discord.Embed()
        embed.title = _map["name"]["en_US"]
        embed.set_thumbnail(url=_map["thumbnail"])
        embed.set_footer(text=f"Type: {_map['type'] or 'N/A'}")
        return embed

    @commands.group(invoke_without_command=True)
    async def random(self, ctx, command: str = None):
        """Returns a random hero, role or map."""
        embed = self.bot.get_subcommands(ctx, ctx.command)
        await ctx.send(embed=embed)

    @random.command(invoke_without_command=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def hero(self, ctx, category: HeroCategory = None):
        """Returns a random hero to play.

        `[category]` - The category to get a random hero from.

        Categories
        - Damage (dps)
        - Support (heal, healear)
        - Tank

        If no category is passed, a random hero is chosen from all categories.
        """
        try:
            embed = await self.random_hero(category)
        except IndexError:
            await ctx.send(
                f'Invalid category. Use "{ctx.prefix}help random hero" to see the available categories.'
            )
        except Exception as exc:
            await ctx.send(exc)
            await ctx.send("Something bad happened. Please try again.")
        else:
            await ctx.send(embed=embed)

    @random.command()
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def role(self, ctx):
        """Returns a random role to play."""
        try:
            embed = self.random_role()
        except Exception:
            await ctx.send("Something bad happened. Please try again.")
        else:
            await ctx.send(embed=embed)

    @random.command(invoke_without_command=True)
    @commands.cooldown(1, 3.0, commands.BucketType.user)
    async def map(self, ctx, category: MapCategory = None):
        """Returns a random map.

        `[category]` - The category to get a random map from.

        Categories
        - Assault
        - Control
        - Escort
        - Hybrid

        If no category is passed, a random map is chosen from all categories.
        """
        try:
            embed = await self.random_map(category)
        except IndexError:
            await ctx.send(
                f'Invalid category. Use "{ctx.prefix}help random map" to see the available categories.'
            )
        except Exception:
            await ctx.send("Something bad happened. Please try again.")
        else:
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Random(bot))
