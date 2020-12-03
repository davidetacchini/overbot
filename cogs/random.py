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
    def filter_by_category(items, path, category):
        return [i for i in items if i[path] == category]

    async def get_random_hero(self, category):
        heroes = await self.get(self.bot.config.random["hero"])

        if not category:
            random_hero = secrets.choice(heroes)
        else:
            categorized_heroes = self.filter_by_category(heroes, "role", category)
            random_hero = secrets.choice(categorized_heroes)

        embed = discord.Embed(color=self.get_hero_color(random_hero))
        embed.title = random_hero["name"].upper()
        embed.set_thumbnail(url=random_hero["portrait"])

        for role in ROLES:
            if role["name"] == random_hero["role"]:
                icon = role["icon"]

        embed.set_footer(
            text=random_hero["role"].capitalize(),
            icon_url=icon,
        )
        return embed

    @staticmethod
    def get_random_role():
        random_role = secrets.choice(ROLES)
        embed = discord.Embed(color=random_role["color"])
        embed.title = random_role["name"].upper()
        embed.set_thumbnail(url=random_role["icon"])
        return embed

    async def get_random_map(self, category):
        maps = await self.get(self.bot.config.random["map"])

        if not category:
            random_map = secrets.choice(maps)
        else:
            categorized_maps = self.filter_by_category(maps, "type", category)
            random_map = secrets.choice(categorized_maps)

        embed = discord.Embed()
        embed.title = random_map["name"]["en_US"]
        embed.set_thumbnail(url=random_map["thumbnail"])
        embed.set_footer(text=f"Type: {random_map['type'] or 'N/A'}")
        return embed

    @commands.group(invoke_without_command=True)
    async def random(self, ctx, command: str = None):
        """Returns a random hero, role or map."""
        embed = self.bot.get_subcommands(ctx, ctx.command)
        await ctx.send(embed=embed)

    @random.command(invoke_without_command=True)
    @commands.cooldown(1, 3.0, commands.BucketType.member)
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
            embed = await self.get_random_hero(category)
        except IndexError:
            await ctx.send(
                f'Invalid category. Use "{ctx.prefix}help random hero" for more info.'
            )
        except Exception as exc:
            await ctx.send(exc)
            await ctx.send("Something bad happened. Please try again.")
        else:
            await ctx.send(embed=embed)

    @random.command()
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    async def role(self, ctx):
        """Returns a random role to play."""
        try:
            embed = self.get_random_role()
        except Exception:
            await ctx.send("Something bad happened. Please try again.")
        else:
            await ctx.send(embed=embed)

    @random.command(invoke_without_command=True)
    @commands.cooldown(1, 3.0, commands.BucketType.member)
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
            embed = await self.get_random_map(category)
        except IndexError:
            await ctx.send(
                f'Invalid category. Use "{ctx.prefix}help random map" for more info.'
            )
        except Exception:
            await ctx.send("Something bad happened. Please try again.")
        else:
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Random(bot))
