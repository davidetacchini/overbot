import discord

from discord.ext import commands

from utils.scrape import get_overwatch_news


class Overwatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def status(self, ctx):
        """Returns Overwatch server status link."""
        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        embed.description = f"[Overwatch Servers Status]({self.bot.config.overwatch['status']})"
        embed.set_footer(text="downdetector.com")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 60.0, commands.BucketType.member)
    async def news(self, ctx, amount: int = 4):
        """Shows the latest Overwatch news.

        `[amount]` - The amount of news to return. Defaults to 4.
        """
        pages = []

        try:
            news = await get_overwatch_news(abs(amount))
        except Exception:
            embed = discord.Embed(color=self.bot.color(ctx.author.id))
            url = self.bot.config.overwatch["news"]
            embed.description = f"[Latest Overwatch News]({url})"
            return await ctx.send(embed=embed)

        for i, n in enumerate(news, start=1):
            embed = discord.Embed(color=self.bot.color(ctx.author.id))
            embed.title = n["title"]
            embed.url = n["link"]
            embed.set_author(name="Blizzard Entertainment")
            embed.set_image(url=f'https:{n["thumbnail"]}')
            embed.set_footer(
                text="News {current}/{total} - {date}".format(
                    current=i, total=len(news), date=n["date"]
                )
            )
            pages.append(embed)

        await self.bot.paginate(pages, ctx=ctx)

    @commands.command()
    async def patch(self, ctx):
        """Returns Overwatch patch notes links."""
        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        embed.title = "Overwatch Patch Notes"
        categories = ["Live", "PTR", "Experimental"]
        description = []
        for category in categories:
            link = self.bot.config.overwatch["patch"].format(category.lower())
            description.append(f"[{category}]({link})")
        embed.description = " - ".join(description)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Overwatch(bot))
