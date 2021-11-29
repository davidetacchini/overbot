from discord.ext import commands

from classes.profile import Profile
from classes.converters import Hero


def valid_platform(argument):
    valid = {
        "pc": "pc",
        "bnet": "pc",
        "xbl": "xbl",
        "xbox": "xbl",
        "ps": "psn",
        "psn": "psn",
        "ps4": "psn",
        "ps5": "psn",
        "play": "psn",
        "playstation": "psn",
        "nsw": "nintendo-switch",
        "switch": "nintendo-switch",
        "nintendo-switch": "nintendo-switch",
    }

    try:
        platform = valid[argument.lower()]
    except KeyError:
        raise commands.BadArgument("Unknown platform.") from None
    return platform


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def show_stats_for(self, ctx, hero, platform, username):
        profile = Profile(platform, username, ctx=ctx)
        await profile.compute_data()
        if profile.is_private():
            embed = profile.embed_private()
        else:
            embed = profile.embed_stats(hero)
        await self.bot.paginate(embed, ctx=ctx)

    @commands.command(aliases=["sr"])
    async def rating(self, ctx, platform: valid_platform, *, username):
        """Returns player ratings.

        `<platform>` - The platform of the player to get the SRs for.
        `<username>` - The username of the player to get the SRs for.

        Platforms:
        - pc, bnet
        - playstation, ps, psn, ps4, ps5, play
        - xbox, xbl
        - nintendo-switch, nsw, switch

        Username:
        - pc: BattleTag (format: name#0000)
        - playstation: Online ID
        - xbox: Gamertag
        - nintendo-switch: Nintendo Network ID
        """
        profile = Profile(platform, username, ctx=ctx)
        await profile.compute_data()
        if profile.is_private():
            embed = profile.embed_private()
        else:
            embed = await profile.embed_ratings()
        await ctx.send(embed=embed)

    @commands.command()
    async def stats(self, ctx, platform: valid_platform, *, username):
        """Returns player general stats.

        `<platform>` - The platform of the player to get stats for.
        `<username>` - The username of the player to get stats for.

        Platforms:
        - pc, bnet
        - playstation, ps, psn, ps4, ps5, play
        - xbox, xbl
        - nintendo-switch, nsw, switch

        Username:
        - pc: BattleTag (format: name#0000)
        - playstation: Online ID
        - xbox: Gamertag
        - nintendo-switch: Nintendo Network ID
        """
        await self.show_stats_for(ctx, "allHeroes", platform, username)

    @commands.command()
    async def hero(
        self,
        ctx,
        hero: Hero,
        platform: valid_platform,
        *,
        username,
    ):
        """Returns player general stats for a given hero.

        `<hero>` - The name of the hero to get the stats for.
        `<platform>` - The platform of the player to get stats for.
        `<username>` - The username of the player to get stats for.

        Platforms:
        - pc, bnet
        - playstation, ps, psn, ps4, ps5, play
        - xbox, xbl
        - nintendo-switch, nsw, switch

        Username:
        - pc: BattleTag (format: name#0000)
        - playstation: Online ID
        - xbox: Gamertag
        - nintendo-switch: Nintendo Network ID
        """
        await self.show_stats_for(ctx, hero, platform, username)

    @commands.command()
    async def summary(self, ctx, platform: valid_platform, *, username):
        """Returns player summarized stats.

        `<platform>` - The platform of the player to get the summary for.
        `<username>` - The username of the player to get the summary for.

        Platforms:
        - pc, bnet
        - playstation, ps, psn, ps4, ps5, play
        - xbox, xbl
        - nintendo-switch, nsw, switch

        Username:
        - pc: BattleTag (format: name#0000)
        - playstation: Online ID
        - xbox: Gamertag
        - nintendo-switch: Nintendo Network ID
        """
        profile = Profile(platform, username, ctx=ctx)
        await profile.compute_data()
        if profile.is_private():
            embed = profile.embed_private()
        else:
            embed = profile.embed_summary()
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Stats(bot))
