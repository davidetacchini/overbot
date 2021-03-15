import secrets

import discord
from discord.ext import commands

from utils.i18n import _, locale
from utils.scrape import get_overwatch_maps
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
    def filter_heroes_by_role(heroes, category):
        return [h for h in heroes if h["role"] == category]

    @staticmethod
    def filter_maps_by_type(maps, *, category):
        return [m for m in maps if category in m["types"]]

    async def get_random_hero(self, category):
        heroes = await self.get(self.bot.config.random["hero"])

        if not category:
            random_hero = secrets.choice(heroes)
        else:
            categorized_heroes = self.filter_heroes_by_role(heroes, category=category)
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

    async def get_random_map(self, ctx, category):
        locale = self.bot.locales[ctx.author.id]
        maps = await get_overwatch_maps(locale)

        if not category:
            random_map = secrets.choice(maps)
        else:
            categorized_maps = self.filter_maps_by_type(maps, category=category)
            random_map = secrets.choice(categorized_maps)

        embed = discord.Embed()
        embed.title = random_map["name"]
        embed.set_image(url=random_map["image_url"])
        embed.set_thumbnail(url=random_map["flag_url"])
        embed.set_footer(text="Type(s): " + ", ".join(random_map["types"]))
        return embed

    @commands.group(invoke_without_command=True)
    @locale
    async def random(self, ctx, command: str = None):
        _("""Returns a random hero, role or map.""")
        embed = self.bot.get_subcommands(ctx, ctx.command)
        await ctx.send(embed=embed)

    @random.command(invoke_without_command=True)
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    @locale
    async def hero(self, ctx, category: HeroCategory = None):
        _(
            """Returns a random hero to play.

        `[category]` - The category to get a random hero from.

        Categories
        - Damage (dps)
        - Support (heal, healear)
        - Tank

        If no category is passed, a random hero is chosen from all categories.
        """
        )
        try:
            embed = await self.get_random_hero(category)
        except IndexError:
            await ctx.send(
                _(
                    'Invalid category. Use "{prefix}help random hero" for more info.'
                ).format(prefix=ctx.prefix)
            )
        except Exception:
            await ctx.send(_("Something bad happened. Please try again."))
        else:
            await ctx.send(embed=embed)

    @random.command()
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    @locale
    async def role(self, ctx):
        _("""Returns a random role to play.""")
        try:
            embed = self.get_random_role()
        except Exception:
            await ctx.send(_("Something bad happened. Please try again."))
        else:
            await ctx.send(embed=embed)

    @random.command(invoke_without_command=True)
    @commands.cooldown(1, 3.0, commands.BucketType.member)
    @locale
    async def map(self, ctx, *, category: MapCategory = None):
        _(
            """Returns a random map.

        `[category]` - The category to get a random map from.

        Categories
        - Control
        - Assault
        - Escort
        - Capture the Flag
        - Hybrid
        - Elimination
        - Deathmatch
        - Team Deathmatch

        If no category is passed, a random map is chosen from all categories.
        """
        )
        try:
            embed = await self.get_random_map(ctx, category)
        except IndexError:
            await ctx.send(
                _(
                    'Invalid category. Use "{prefix}help random map" for more info.'
                ).format(prefix=ctx.prefix)
            )
        except Exception:
            await ctx.send(_("Something bad happened. Please try again."))
        else:
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Random(bot))
