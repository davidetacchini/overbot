import secrets

import discord
from discord.ext import commands

from utils.i18n import _, locale

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


def valid_hero_cat(argument):
    valid = {
        "tank": "tank",
        "damage": "damage",
        "dps": "damage",
        "support": "support",
        "healer": "support",
        "heal": "support",
    }

    try:
        category = valid[argument.lower()]
    except KeyError:
        raise commands.BadArgument(_("Unknown hero category.")) from None
    return category


def valid_map_cat(argument):
    valid = {
        "control": "control",
        "assault": "assault",
        "escort": "escort",
        "capture the flag": "capture the flag",
        "ctf": "capture the flag",
        "hybrid": "hybrid",
        "elimination": "elimination",
        "deathmatch": "deathmatch",
        "team deathmatch": "team deathmatch",
        "tdm": "team deathmatch",
    }

    try:
        category = valid[argument.lower()]
    except KeyError:
        raise commands.BadArgument(_("Unknown map category.")) from None
    return category


def valid_meme_cat(argument):
    argument = argument.lower()
    if argument not in ("hot", "new", "top", "rising"):
        raise commands.BadArgument(_("Unknown meme category."))
    return argument


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def get_hero_color(hero):
        if hero["role"] == "tank":
            return 0xFAA528
        elif hero["role"] == "damage":
            return 0xE61B23
        return 0x13A549

    @staticmethod
    def get_random_role():
        role = secrets.choice(ROLES)
        embed = discord.Embed(color=role["color"])
        embed.set_author(name=role["name"].capitalize(), icon_url=role["icon"])
        return embed

    async def get_random_hero(self, category):
        heroes = self.bot.heroes

        if not category:
            hero = secrets.choice(heroes)
        else:
            categorized_heroes = [h for h in heroes if h["role"] == category]
            hero = secrets.choice(categorized_heroes)

        embed = discord.Embed(color=self.get_hero_color(hero))
        embed.set_author(name=hero["name"], icon_url=hero["portrait"])
        return embed

    async def get_random_map(self, ctx, category):
        maps = self.bot.maps

        if not category:
            _map = secrets.choice(maps)
        else:
            categorized_maps = [m for m in maps if category in m["types"]]
            _map = secrets.choice(categorized_maps)

        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        embed.set_author(name=_map["name"], icon_url=_map["flag_url"])
        embed.set_thumbnail(url=_map["image_url"])
        embed.set_footer(text=", ".join(_map["types"]))
        return embed

    async def get_meme(self, category):
        url = f"https://www.reddit.com/r/Overwatch_Memes/{category}.json"
        async with self.bot.session.get(url) as r:
            memes = await r.json()
        # excluding .mp4 and files from other domains
        memes = [
            meme
            for meme in memes["data"]["children"]
            if not meme["data"]["secure_media"]
            or not meme["data"]["is_reddit_media_domain"]
        ]
        return secrets.choice(memes)

    def embed_meme(self, ctx, meme):
        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        embed.title = meme["data"]["title"]
        embed.description = "{upvotes} upvotes - {comments} comments".format(
            upvotes=meme["data"]["ups"], comments=meme["data"]["num_comments"]
        )
        embed.url = f'https://reddit.com{meme["data"]["permalink"]}'
        embed.set_image(url=meme["data"]["url"])
        embed.set_footer(text=meme["data"]["subreddit_name_prefixed"])
        return embed

    @commands.command(aliases=["htp"])
    @locale
    async def herotoplay(self, ctx, category: valid_hero_cat = None):
        _(
            """Returns a random hero to play.

        `[category]` - The category to get a random hero from.

        Categories:

        - damage, dps
        - support, heal, healer
        - tank

        If no category is passed in, a random hero is chosen from all categories.
        """
        )
        embed = await self.get_random_hero(category)
        await ctx.send(embed=embed)

    @commands.command(aliases=["rtp"])
    @locale
    async def roletoplay(self, ctx):
        _("""Returns a random role to play.""")
        embed = self.get_random_role()
        await ctx.send(embed=embed)

    @commands.command(aliases=["mtp"])
    @locale
    async def maptoplay(self, ctx, *, category: valid_map_cat = None):
        _(
            """Returns a random map.

        `[category]` - The category to get a random map from.

        Categories:

        - control
        - assault
        - escort
        - capture the flag, ctf
        - hybrid
        - elimination
        - deathmatch
        - team deathmatch, tdm

        If no category is passed in, a random map is chosen from all categories.
        """
        )
        embed = await self.get_random_map(ctx, category)
        await ctx.send(embed=embed)

    @commands.command()
    @locale
    async def meme(self, ctx, category: valid_meme_cat = "hot"):
        _(
            """Returns a random Overwatch meme.

        `[category]` - The category to get a random meme from. Defaults to `Hot`.

        Categories:

        - hot
        - new
        - top
        - rising

        All memes are taken from the subreddit r/Overwatch_Memes.
        """
        )
        meme = await self.get_meme(category)
        embed = self.embed_meme(ctx, meme)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Fun(bot))
