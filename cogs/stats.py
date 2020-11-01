from discord.ext import commands

from utils.data import RequestError
from utils.player import Player, NoStatistics, NoHeroStatistics
from classes.converters import Hero, Platform


class Statistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["rating"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rank(self, ctx, platform: Platform, *, username):
        """Returns player ranks."""
        async with ctx.typing():
            try:
                data = await self.bot.data.Data(platform=platform, name=username).get()
            except RequestError as exc:
                await ctx.send(exc)
            except Exception as exc:
                await ctx.send(embed=self.bot.embed_exception(exc))
            else:
                try:
                    profile = Player(data=data, platform=platform, name=username)
                    if profile.is_private:
                        embed = profile.private(ctx)
                    else:
                        embed = profile.rank()
                except Exception as exc:
                    await ctx.send(embed=self.bot.embed_exception(exc))
                else:
                    await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stats(self, ctx, platform: Platform, *, username):
        """Returns player both quick play and competitive statistics."""
        async with ctx.typing():
            try:
                data = await self.bot.data.Data(platform=platform, name=username).get()
            except RequestError as exc:
                await ctx.send(exc)
            except Exception as exc:
                await ctx.send(embed=self.bot.embed_exception(exc))
            else:
                try:
                    profile = Player(data=data, platform=platform, name=username)
                    if profile.is_private:
                        embed = profile.private(ctx)
                    else:
                        embed = profile.statistics(ctx)
                except NoStatistics as exc:
                    await ctx.send(exc)
                except Exception as exc:
                    await ctx.send(embed=self.bot.embed_exception(exc))
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
        username,
    ):
        """Returns player both quick play and competitive statistics for a given hero."""
        async with ctx.typing():
            try:
                data = await self.bot.data.Data(platform=platform, name=username).get()
            except RequestError as exc:
                await ctx.send(exc)
            except Exception as exc:
                await ctx.send(embed=self.bot.embed_exception(exc))
            else:
                try:
                    profile = Player(data=data, platform=platform, name=username)
                    if profile.is_private:
                        embed = profile.private(ctx)
                    else:
                        embed = profile.hero(ctx, hero)
                except NoHeroStatistics as exc:
                    await ctx.send(exc)
                except Exception as exc:
                    await ctx.send(embed=self.bot.embed_exception(exc))
                else:
                    await self.bot.paginator.Paginator(extras=embed).paginate(ctx)


def setup(bot):
    bot.add_cog(Statistics(bot))
