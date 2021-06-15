import discord

from discord.ext import commands

from utils.i18n import _, locale
from utils.scrape import (
    get_overwatch_news,
    get_overwatch_status,
    get_overwatch_patch_notes,
)

STATUSES = [
    "no problems at overwatch",
    "user reports indicate no current problems at overwatch",
]


class Overwatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_overwatch_status(self, status):
        if status.lower() in STATUSES:
            return (f"<:online:648186001361076243> {status}", discord.Color.green())
        return (f"<:dnd:648185968209428490> {status}", discord.Color.red())

    @commands.command()
    @commands.cooldown(1, 30.0, commands.BucketType.member)
    @locale
    async def status(self, ctx):
        _(
            """Returns the current Overwatch servers status.

        You can use this command once every 30 seconds.
        """
        )
        embed = discord.Embed()
        embed.title = "Overwatch"
        embed.url = self.bot.config.overwatch["status"]
        embed.timestamp = ctx.message.created_at
        embed.set_footer(text="downdetector.com")

        try:
            overwatch = await get_overwatch_status()
        except Exception:
            embed.color = self.bot.color(ctx.author.id)
            embed.description = (
                f"[Overwatch Servers Status]({self.bot.config.overwatch['status']})"
            )
        else:
            status, color = self.format_overwatch_status(str(overwatch).strip())
            embed.color = color
            embed.description = status
        await ctx.send(embed=embed)

    @commands.command()
    @commands.cooldown(1, 30.0, commands.BucketType.member)
    @locale
    async def news(self, ctx, amount: int = 4):
        _(
            """Returns the latest Overwatch news.

        `[amount]` - The amount of news to return. Defaults to 4.

        You can use this command once every 30 seconds.
        """
        )
        async with ctx.typing():
            pages = []

            try:
                locale = self.bot.locales.get(ctx.author.id)
                titles, links, imgs, dates = await get_overwatch_news(
                    locale, amount=abs(amount)
                )
            except Exception:
                embed = discord.Embed(color=self.bot.color(ctx.author.id))
                embed.title = _("Latest Overwatch News")
                embed.description = _("[Click here]({news})").format(
                    news=self.bot.config.overwatch["news"]
                )
                return await ctx.send(embed=embed)

            for i, (title, link, img, date) in enumerate(
                zip(titles, links, imgs, dates), start=1
            ):
                embed = discord.Embed(color=self.bot.color(ctx.author.id))
                embed.title = title
                embed.url = link
                embed.set_author(name="Blizzard Entertainment")
                embed.set_image(url=f"https:{img}")
                embed.set_footer(
                    text=_("News {current}/{total} - {date}").format(
                        current=i, total=len(titles), date=date
                    )
                )
                pages.append(embed)

            await self.bot.paginator.Paginator(pages=pages).start(ctx)

    @commands.command()
    @commands.cooldown(1, 30.0, commands.BucketType.member)
    @locale
    async def patch(self, ctx):
        _(
            """Returns patch notes links.

        You can use this command once every 30 seconds.
        """
        )
        locale = self.bot.locales[ctx.author.id].lower()
        embed = discord.Embed(color=self.bot.color(ctx.author.id))
        embed.title = _("Overwatch Patch Notes")
        live, ptr, experimental = await get_overwatch_patch_notes(ctx)
        categories = {"live": live, "ptr": ptr, "experimental": experimental}
        for key, value in categories.items():
            text = _("[Click here to view **{category}** patch notes]({link})").format(
                category=value,
                link=self.bot.config.overwatch["patch"].format(locale, key),
            )
            embed.add_field(name=value, value=text, inline=False)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Overwatch(bot))
