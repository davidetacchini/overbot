from discord.ext import commands

from utils.i18n import _, locale
from utils.player import Player, PlayerException
from utils.request import Request, RequestError
from classes.converters import Hero


def valid_platform(argument):
    valid = {
        "pc": "pc",
        "bnet": "pc",
        "xbl": "xbl",
        "xbox": "xbl",
        "ps": "psn",
        "psn": "psn",
        "play": "psn",
        "playstation": "psn",
        "nsw": "nintendo-switch",
        "switch": "nintendo-switch",
        "nintendo-switch": "nintendo-switch",
    }

    try:
        platform = valid[argument.lower()]
    except KeyError:
        raise commands.BadArgument(_("Unknown platform.")) from None

    return platform


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def show_stats_for(self, ctx, platform, username):
        try:
            data = await Request(platform=platform, username=username).get()
        except RequestError as e:
            return await ctx.send(e)

        profile = Player(data, platform=platform, username=username)
        if profile.is_private:
            embed = profile.private()
        else:
            try:
                embed = profile.get_stats(ctx)
            except PlayerException as e:
                return await ctx.send(e)
        await self.bot.paginator.Paginator(pages=embed).start(ctx)

    async def show_hero_stats_for(self, ctx, hero, platform, username):
        try:
            data = await Request(platform=platform, username=username).get()
        except RequestError as e:
            return await ctx.send(e)

        profile = Player(data, platform=platform, username=username)
        if profile.is_private:
            embed = profile.private()
        else:
            try:
                embed = profile.get_hero(ctx, hero)
            except PlayerException as e:
                return await ctx.send(e)
        await self.bot.paginator.Paginator(pages=embed).start(ctx)

    @commands.command(aliases=["rank", "sr"])
    @locale
    async def rating(self, ctx, platform: valid_platform, *, username):
        _(
            """Returns player ratings.

        `<platform>` - The platform of the player to get ranks for.
        `<username>` - The username of the player to get ranks for.

        Platforms:

        - pc, bnet
        - playstation, ps, psn, play
        - xbox, xbl
        - nintendo-switch, nsw, switch

        Username:

        - pc: BattleTag (format: name#0000)
        - playstation: Online ID
        - xbox: Gamertag
        - nintendo-switch: Nintendo Switch ID (format: name-code)
        """
        )
        async with ctx.fetching():
            try:
                data = await Request(platform=platform, username=username).get()
            except RequestError as e:
                return await ctx.send(e)

            profile = Player(data, platform=platform, username=username)
            if profile.is_private:
                embed = profile.private()
            else:
                embed = await profile.get_ratings(ctx)
            await ctx.send(embed=embed)

    @commands.command()
    @locale
    async def stats(self, ctx, platform: valid_platform, *, username):
        _(
            """Returns player both quick play and competitive stats.

        `<platform>` - The platform of the player to get stats for.
        `<username>` - The username of the player to get stats for.

        Platforms:

        - pc, bnet
        - playstation, ps, psn, play
        - xbox, xbl
        - nintendo-switch, nsw, switch

        Username:

        - pc: BattleTag (format: name#0000)
        - playstation: Online ID
        - xbox: Gamertag
        - nintendo-switch: Nintendo Switch ID (format: name-code)
        """
        )
        async with ctx.fetching():
            await self.show_stats_for(ctx, platform, username)

    @commands.command()
    @locale
    async def hero(
        self,
        ctx,
        hero: Hero,
        platform: valid_platform,
        *,
        username,
    ):
        _(
            """Returns player both quick play and competitive stats for a given hero.

        `<hero>` - The name of the hero you want to see stats for.
        `<platform>` - The platform of the player to get stats for.
        `<username>` - The username of the player to get stats for.

        Platforms:

        - pc, bnet
        - playstation, ps, psn, play
        - xbox, xbl
        - nintendo-switch, nsw, switch

        Username:

        - pc: BattleTag (format: name#0000)
        - playstation: Online ID
        - xbox: Gamertag
        - nintendo-switch: Nintendo Switch ID (format: name-code)
        """
        )
        async with ctx.fetching():
            await self.show_hero_stats_for(ctx, hero, platform, username)


def setup(bot):
    bot.add_cog(Stats(bot))
