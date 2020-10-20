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
            try:
                embed = Player(data=data, platform=platform, name=username).rank()
            except Exception as exc:
                await ctx.send(embed=embed_exception(exc))
            else:
                await ctx.send(embed=embed)

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
            try:
                embed = Player(data=data, platform=platform, name=username).statistics(
                    ctx
                )
            except NoStatistics as exc:
                await ctx.send(exc)
            except Exception as exc:
                await ctx.send(embed=embed_exception(exc))
            else:
                await self.bot.paginator.Paginator(extras=embed).paginate(ctx)

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
            try:
                embed = Player(data=data, platform=platform, name=username).hero(
                    ctx, hero
                )
            except NoHeroStatistics as exc:
                await ctx.send(exc)
            except Exception as exc:
                await ctx.send(embed=embed_exception(exc))
            else:
                await self.bot.paginator.Paginator(extras=embed).paginate(ctx)


def setup(bot):
    bot.add_cog(Statistics(bot))
