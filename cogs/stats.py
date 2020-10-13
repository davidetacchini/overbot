from discord.ext import commands

from utils.embed import CustomEmbed, NoStatistics, NoHeroStatistics
from utils.globals import embed_exception
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
            if r.status != 200:
                return await ctx.send(
                    "Profile not found. Please try again and make sure you didn't miss any capital letter."
                )
            data = await r.json()

        profile = CustomEmbed(data=data, platform=platform, name=name)

        try:
            if profile.is_private:
                embed = profile.private(ctx)
            elif command == "rank":
                embed = profile.rank()
            elif command == "hero":
                embed = profile.hero(ctx, hero)
            else:
                embed = profile.statistics(ctx)
            try:
                await ctx.bot.paginator.Paginator(extras=embed).paginate(ctx)
            except TypeError:  # if there is just one page
                await ctx.send(embed=embed)
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
        """Returns player rank.

        Arguments
            - platform: must be pc, psn or xbl.
            - name: battletag if platform is pc else your console gamertag.
            Please note that the name is case sensitive.
        """
        async with ctx.typing():
            await self.embed_stats(ctx, platform, username)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stats(self, ctx, platform: Platform, *, username: Username):
        """Returns player both competitive and quick play statistics.

        Arguments
            - platform: must be pc, psn or xbl.
            - name: battletag if platform is pc else your console gamertag.
            Please note that the name is case sensitive.
        """
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
        """Returns player stats for a given hero.

        Arguments
            - hero: the hero name you want to see the stats for.
            - platform: must be pc, psn or xbl.
            - name: battletag if platform is pc else your console gamertag.
            Please note that the name is case sensitive.
        """
        async with ctx.typing():
            await self.embed_stats(ctx, platform, username, hero)


def setup(bot):
    bot.add_cog(Statistics(bot))
