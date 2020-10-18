from discord.ext import commands

from utils.globals import embed_exception
from utils.profile import Profile, NoStatistics, NoHeroStatistics
from classes.converters import Hero, Platform, Username


class Statistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    async def embed_stats(ctx, platform, name, hero=None):
        """Returns players formatted stats."""
        url = f"{ctx.bot.config.base_url}/{platform}/{name}/complete"
        command = str(ctx.command.name).lower()

        async with ctx.bot.session.get(url) as r:
            if r.status == 200:
                data = await r.json()
            elif r.status == 400:
                return await ctx.send(
                    f"Wrong battletag format! Correct format: {name}#0000"
                )
            elif r.status == 404:
                return await ctx.send(
                    "Profile not found. Please make sure you aren't missing any capital letter."
                )
            elif r.status == 500:
                return await ctx.send(
                    "API Internal server error. Please be patiente and try again."
                )
            else:
                return await ctx.send(
                    "The API is under maintenance. Please be patiente and try again later."
                )

        profile = Profile(data=data, platform=platform, name=name)

        try:
            if profile.is_private:
                embed = profile.private(ctx)
            elif command == "rank":
                embed = profile.rank()
            elif command == "hero":
                embed = profile.hero(ctx, hero)
            else:
                embed = profile.statistics(ctx)
            await ctx.bot.paginator.Paginator(extras=embed).paginate(ctx)
        except NoStatistics:
            await ctx.send(
                "This profile has no quick play nor competitive statistics to display."
            )
        except NoHeroStatistics:
            await ctx.send(
                f"This profile has no quick play nor competitive stats for **{hero}** to display."
            )
        except Exception as exc:
            await ctx.send(embed=embed_exception(exc))

    @commands.command(aliases=["rating"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rank(self, ctx, platform: Platform, *, username: Username):
        """Returns player rank."""
        async with ctx.typing():
            await self.embed_stats(ctx, platform, username)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stats(self, ctx, platform: Platform, *, username: Username):
        """Returns player both competitive and quick play statistics."""
        async with ctx.typing():
            await self.embed_stats(ctx, platform, username)

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
            await self.embed_stats(ctx, platform, username, hero)


def setup(bot):
    bot.add_cog(Statistics(bot))
