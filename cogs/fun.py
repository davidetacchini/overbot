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


def hero_cat(argument):
    argument = argument.lower()
    valid = ("tank", "damage", "dps", "support", "healer", "heal")
    if argument not in valid:
        raise commands.BadArgument(_("Unknown hero category."))
    elif argument in ("heal", "healer"):
        return "support"
    elif argument == "dps":
        return "damage"
    return argument


def map_cat(argument):
    return argument.lower()


def meme_cat(argument):
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
        random_role = secrets.choice(ROLES)
        embed = discord.Embed(color=random_role["color"])
        embed.set_author(
            name=random_role["name"].capitalize(), icon_url=random_role["icon"]
        )
        return embed

    async def get_random_hero(self, category):
        heroes = self.bot.heroes

        if not category:
            random_hero = secrets.choice(heroes)
        else:
            categorized_heroes = [h for h in heroes if h["role"] == category]
            random_hero = secrets.choice(categorized_heroes)

        embed = discord.Embed(color=self.get_hero_color(random_hero))
        embed.set_author(name=random_hero["name"], icon_url=random_hero["portrait"])
        return embed

    async def get_random_map(self, ctx, category):
        maps = self.bot.maps

        if not category:
            random_map = secrets.choice(maps)
        else:
            categorized_maps = [m for m in maps if category in m["types"]]
            random_map = secrets.choice(categorized_maps)

        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        embed.set_author(name=random_map["name"], icon_url=random_map["flag_url"])
        embed.set_thumbnail(url=random_map["image_url"])
        embed.set_footer(text="Type(s): " + ", ".join(random_map["types"]))
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
    async def herotoplay(self, ctx, category: hero_cat = None):
        _(
            """Returns a random hero to play.

        `[category]` - The category to get a random hero from.

        Categories:

        - Damage (dps)
        - Support (heal, healear)
        - Tank

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
    async def maptoplay(self, ctx, *, category: map_cat = None):
        _(
            """Returns a random map.

        `[category]` - The category to get a random map from.

        Categories:

        - Control
        - Assault
        - Escort
        - Capture the Flag
        - Hybrid
        - Elimination
        - Deathmatch
        - Team Deathmatch

        If no category is passed in, a random map is chosen from all categories.
        """
        )
        try:
            embed = await self.get_random_map(ctx, category)
        except IndexError:
            await ctx.send(_("Unknown map category."))
        else:
            await ctx.send(embed=embed)

    @commands.command()
    @locale
    async def meme(self, ctx, category: meme_cat = "hot"):
        _(
            """Returns a random Overwatch meme.

        `[category]` - The category to get a random meme from. Defaults to `Hot`.

        Categories:

        - Hot
        - New
        - Top
        - Rising

        All memes are taken from the subreddit r/Overwatch_Memes.
        """
        )
        try:
            meme = await self.get_meme(category)
            embed = self.embed_meme(ctx, meme)
        except Exception as e:
            await ctx.send(embed=self.bot.embed_exception(e))
        else:
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Fun(bot))
