from discord.ext import commands

from utils.data import RequestError
from utils.player import Player, PlayerException
from classes.converters import Hero, Platform


class Statistics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["rating"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def rank(self, ctx, platform: Platform, *, username):
        """Returns player ranks.

        `<platform>` - The platform of the player to get ranks for.
        `<username>` - The username of the player to get ranks for.

        Available platforms
        - pc
        - playstation (ps, psn, play)
        - xbox (xbl)
        - nintendo-switch (nsw, switch)

        Username formatting
        - pc: Battletag (format: name#0000)
        - playstation: Online ID
        - xbox: Gamertag
        - nintendo-switch: Nintendo Switch ID (format: name-code)

        Battletag example: Smyile#2825
        Nintendo Switch ID example: name-7alf327e36d5d1d8f507e765u5a2ech7
        """
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

    @commands.command(aliases=["stats"])
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def statistics(self, ctx, platform: Platform, *, username):
        """Returns player both quick play and competitive statistics.

        `<platform>` - The platform of the player to get stats for.
        `<username>` - The username of the player to get stats for.

        Available platforms
        - pc
        - playstation (ps, psn, play)
        - xbox (xbl)
        - nintendo-switch (nsw, switch)

        Username formatting
        - pc: Battletag (format: name#0000)
        - playstation: Online ID
        - xbox: Gamertag
        - nintendo-switch: Nintendo Switch ID (format: name-code)

        Battletag example: Smyile#2825
        Nintendo Switch ID example: name-7alf327e36d5d1d8f507e765u5a2ech7
        """
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
                except PlayerException as exc:
                    await ctx.send(exc)
                except Exception as exc:
                    await ctx.send(embed=self.bot.embed_exception(exc))
                else:
                    await self.bot.paginator.Paginator(pages=embed).paginate(ctx)

    @commands.command()
    @commands.cooldown(1, 5.0, commands.BucketType.user)
    async def hero(
        self,
        ctx,
        hero: Hero,
        platform: Platform,
        *,
        username,
    ):
        """Returns player both quick play and competitive statistics for a given hero.

        `<Hero>` - The name of the hero you want to see stats for.
        `<platform>` - The platform of the player to get stats for.
        `<username>` - The username of the player to get stats for.

        Available platforms
        - pc
        - playstation (ps, psn, play)
        - xbox (xbl)
        - nintendo-switch (nsw, switch)

        Username formatting
        - pc: Battletag (format: name#0000)
        - playstation: Online ID
        - xbox: Gamertag
        - nintendo-switch: Nintendo Switch ID (format: name-code)

        Battletag example: Smyile#2825
        Nintendo Switch ID example: name-7alf327e36d5d1d8f507e765u5a2ech7
        """
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
                except PlayerException as exc:
                    await ctx.send(exc)
                except Exception as exc:
                    await ctx.send(embed=self.bot.embed_exception(exc))
                else:
                    await self.bot.paginator.Paginator(pages=embed).paginate(ctx)


def setup(bot):
    bot.add_cog(Statistics(bot))
