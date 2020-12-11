import discord
from discord.ext import commands

from utils.scrape import get_overwatch_news, get_overwatch_status


class Overwatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def format_overwatch_status(s):
        if s.lower() == "no problems at overwatch":
            return (f"<:online:648186001361076243> {s}", discord.Color.green())
        return (f"<:dnd:648185968209428490> {s}", discord.Color.red())

    @commands.command()
    @commands.cooldown(1, 60.0, commands.BucketType.member)
    async def status(self, ctx):
        """Returns the current Overwatch servers status."""
        embed = discord.Embed()
        embed.title = "Status"
        embed.url = self.bot.config.overwatch["status"]
        embed.timestamp = self.bot.timestamp
        embed.set_footer(text="downdetector.com")
        try:
            overwatch = await get_overwatch_status()
        except Exception:
            embed.description = (
                f"[Overwatch Servers Status]({self.bot.config.overwatch['status']})"
            )
        else:
            status, color = self.format_overwatch_status(str(overwatch).strip())
            embed.color = color
            embed.add_field(
                name="Overwatch",
                value=status,
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 30.0, commands.BucketType.member)
    async def news(self, ctx, amount: int = None):
        """Returns the latest Overwatch news.

        `[amount]` - The amount of news to return. Default to 4.

        You can use this command once every 30 seconds.
        """
        async with ctx.typing():
            pages = []
            try:
                amount = amount or 4
                titles, links, imgs, dates = await get_overwatch_news(abs(amount))
            except Exception:
                embed = discord.Embed(color=self.bot.color)
                embed.title = "Latest Overwatch News"
                embed.description = f"[Click here]({self.bot.config.overwatch['news']})"
                await ctx.send(embed=embed)
            else:
                for i, (title, link, img, date) in enumerate(
                    zip(titles, links, imgs, dates), start=1
                ):
                    embed = discord.Embed()
                    embed.title = title
                    embed.url = link
                    embed.set_author(name="Blizzard Entertainment")
                    embed.set_image(url=f"https:{img}")
                    embed.set_footer(text=f"News {i}/{len(titles)} • {date}")
                    pages.append(embed)
                await self.bot.paginator.Paginator(pages=pages).start(ctx)

    @commands.command()
    @commands.cooldown(1, 5.0, commands.BucketType.member)
    async def patch(self, ctx):
        """Returns patch notes links."""
        embed = discord.Embed(color=self.bot.color)
        embed.title = "Overwatch Patch Notes"
        embed.add_field(
            name="Live",
            value="[Click here to view **live** patch notes]"
            f"({self.bot.config.overwatch['patch'].format('live')})",
            inline=False,
        )
        embed.add_field(
            name="Ptr",
            value="[Click here to view **ptr** patch notes]"
            f"({self.bot.config.overwatch['patch'].format('ptr')})",
            inline=False,
        )
        embed.add_field(
            name="Experimental",
            value="[Click here to view **experimental** patch notes]"
            f"({self.bot.config.overwatch['patch'].format('experimental')})",
            inline=False,
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Overwatch(bot))
