from discord.ext import commands

from utils.data import RequestError
from utils.player import Player, NoStatistics, NoHeroStatistics
from utils.globals import embed_exception
from classes.converters import Hero, Platform, Username


class Statistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["rating"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rank(self, ctx, platform: Platform, *, username: Username):
        """Returns player ranks."""
        async with ctx.typing():
            try:
                data = await self.bot.data.Data(platform=platform, name=username).get()
            except RequestError as exc:
                await ctx.send(exc)
            except Exception as exc:
                await ctx.send(embed=embed_exception(exc))
            profile = Player(data=data, platform=platform, name=username).rank()
            try:
                await ctx.send(embed=profile)
            except Exception as exc:
                await ctx.send(embed=embed_exception(exc))

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stats(self, ctx, platform: Platform, *, username: Username):
        """Returns player both competitive and quick play statistics."""
        async with ctx.typing():
            try:
                data = await self.bot.data.Data(platform=platform, name=username).get()
            except RequestError as exc:
                await ctx.send(exc)
            except Exception as exc:
                await ctx.send(embed=embed_exception(exc))
            profile = Player(data=data, platform=platform, name=username).statistics(
                ctx
            )
            try:
                await self.bot.paginator.Paginator(extras=profile).paginate(ctx)
            except NoStatistics:
                await ctx.send(
                    "This profile has no quick play nor competitive statistics to display."
                )
            except Exception as exc:
                await ctx.send(embed=embed_exception(exc))

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hero(
        self,
        ctx,
        hero: Hero,
        platform: Platform,
        *,
        username: Username,
    ):
        """Returns player stats for a given hero."""
        async with ctx.typing():
            try:
                data = await self.bot.data.Data(platform=platform, name=username).get()
            except RequestError as exc:
                await ctx.send(exc)
            except Exception as exc:
                await ctx.send(embed=embed_exception(exc))
            profile = Player(data=data, platform=platform, name=username).hero(
                ctx, hero
            )
            try:
                await self.bot.paginator.Paginator(extras=profile).paginate(ctx)
            except NoHeroStatistics:
                await ctx.send(
                    f"This profile has no quick play nor competitive stats for **{hero}** to display."
                )
            except Exception as exc:
                await ctx.send(embed=embed_exception(exc))


def setup(bot):
    bot.add_cog(Statistics(bot))
