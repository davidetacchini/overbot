import discord

from discord.ext import commands

from utils import emojis
from utils.scrape import get_overwatch_news, get_overwatch_status, get_overwatch_patch_notes


class Overwatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_overwatch_status(self, status):
        lookup = (
            "no problems at overwatch",
            "user reports indicate no current problems at overwatch",
        )
        if status.lower() in lookup:
            return (f"{emojis.online} {status}", discord.Color.green())
        return (f"{emojis.dnd} {status}", discord.Color.red())

    @commands.command()
    @commands.cooldown(1, 30.0, commands.BucketType.member)
    async def status(self, ctx):
        """Shows Overwatch servers status.

        You can use this command once every 30 seconds.
        """
        embed = discord.Embed()
        embed.title = "Overwatch"
        embed.url = self.bot.config.overwatch["status"]
        embed.timestamp = ctx.message.created_at
        embed.set_footer(text="downdetector.com")

        try:
            overwatch = await get_overwatch_status()
        except Exception:
            embed.color = self.bot.color(ctx.author.id)
            embed.description = f"[Overwatch Servers Status]({self.bot.config.overwatch['status']})"
        else:
            status, color = self.format_overwatch_status(str(overwatch).strip())
            embed.color = color
            embed.description = status
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 30.0, commands.BucketType.member)
    async def news(self, ctx, amount: int = 4):
        """Shows the latest Overwatch news.

        `[amount]` - The amount of news to return. Defaults to 4.

        You can use this command once every 30 seconds.
        """
        pages = []

        try:
            news = await get_overwatch_news(abs(amount))
        except Exception:
            embed = discord.Embed(color=self.bot.color(ctx.author.id))
            embed.title = "Latest Overwatch News"
            embed.description = "[Click here]({news})".format(
                news=self.bot.config.overwatch["news"]
            )
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
    @commands.cooldown(1, 30.0, commands.BucketType.member)
    async def patch(self, ctx):
        """Returns patch notes links.

        You can use this command once every 30 seconds.
        """
        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        embed.title = "Overwatch Patch Notes"
        live, ptr, experimental = await get_overwatch_patch_notes()
        categories = {"live": live, "ptr": ptr, "experimental": experimental}
        for key, value in categories.items():
            text = "[Click here to view **{category}** patch notes]({link})".format(
                category=value, link=self.bot.config.overwatch["patch"]
            )
            embed.add_field(name=value, value=text, inline=False)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Overwatch(bot))
