import secrets

import discord

from discord.ext import commands

MEME_CATEGORIES = ("hot", "new", "top", "rising")


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
        raise commands.BadArgument("Unknown hero category.") from None
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
        raise commands.BadArgument("Unknown map category.") from None
    return category


def valid_meme_cat(argument):
    argument = argument.lower()
    if argument not in MEME_CATEGORIES:
        raise commands.BadArgument("Unknown meme category.")
    return argument


class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_random_hero(self, category):
        heroes = self.bot.heroes
        if not category:
            hero = secrets.choice(heroes)
        else:
            categorized_heroes = [h for h in heroes if h["role"] == category]
            hero = secrets.choice(categorized_heroes)
        return hero["name"]

    def get_random_map(self, ctx, category):
        maps = self.bot.maps
        if not category:
            map_ = secrets.choice(maps)
        else:
            categorized_maps = [m for m in maps if category in m["types"]]
            map_ = secrets.choice(categorized_maps)
        return map_["name"]

    async def get_meme(self, category):
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

    @commands.command(aliases=["htp"], brief="Returns a random hero.")
    async def herotoplay(self, ctx, category: valid_hero_cat = None):
        """Returns a random hero to play.

        `[category]` - The category to get a random hero from.

        Categories:

        - damage, dps
        - support, heal, healer
        - tank

        If no category is given, a random hero is chosen from all categories.
        """
        hero = self.get_random_hero(category)
        await ctx.send(hero)

    @commands.command(aliases=["rtp"], brief="Returns a random role.")
    async def roletoplay(self, ctx):
        """Returns a random role to play."""
        roles = ("Tank", "Damage", "Support", "Flex")
        await ctx.send(secrets.choice(roles))

    @commands.command(aliases=["mtp"], brief="Returns a random map.")
    async def maptoplay(self, ctx, *, category: valid_map_cat = None):
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

        If no category is given, a random map is chosen from all categories.
        """
        map_ = self.get_random_map(ctx, category)
        await ctx.send(map_)

    @commands.command(brief="Returns a random meme.")
    async def meme(self, ctx, category: valid_meme_cat = None):
        """Returns a random Overwatch meme.

        `[category]` - The category to get a random meme from.

        Categories:

        - hot
        - new
        - top
        - rising

        Memes are taken from the subreddit r/Overwatch_Memes.
        """
        await ctx.send(
            "This command is currently not available because **OverBot"
            " has been rate limited by Reddit**. Sorry for the inconvenience."
        )
        # category = category or secrets.choice(MEME_CATEGORIES)
        # meme = await self.get_meme(category)
        # embed = self.embed_meme(ctx, meme)
        # await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Fun(bot))
