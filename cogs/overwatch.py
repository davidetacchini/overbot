import discord

from discord.ext import commands

from utils.cache import cache
from utils.checks import is_premium
from utils.scrape import get_overwatch_news


class Newsboard:
    __slots__ = ("guild_id", "bot", "record", "channel_id", "member_id")

    def __init__(self, guild_id, bot, *, record=None):
        self.guild_id = guild_id
        self.bot = bot

        if record:
            self.channel_id = record["id"]
            self.member_id = record["member_id"]
        else:
            self.channel_id = None

    @property
    def channel(self):
        guild = self.bot.get_guild(self.guild_id)
        return guild and guild.get_channel(self.channel_id)


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
        categories = ("Live", "PTR", "Experimental")
        description = []
        for category in categories:
            link = self.bot.config.overwatch["patch"].format(category.lower())
            description.append(f"[{category}]({link})")
        embed.description = " - ".join(description)
        await ctx.send(embed=embed)

    @cache()
    async def get_newsboard(self, guild_id):
        query = "SELECT * FROM newsboard WHERE server_id = $1;"
        record = await self.bot.pool.fetchrow(query, guild_id)
        return Newsboard(guild_id, self.bot, record=record)

    async def _has_newsboard(self, member_id: int):
        query = "SELECT server_id FROM newsboard WHERE member_id = $1;"
        guild_id = await self.bot.pool.fetchval(query, member_id)
        return self.bot.get_guild(guild_id)

    @is_premium()
    @commands.group(invoke_without_command=True, extras={"premium": True})
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def newsboard(self, ctx):
        """Creates an Overwatch news channel.

        You must have Manage Channels permission to use this.
        """
        newsboard = await self.get_newsboard(ctx.guild.id)
        if newsboard.channel is not None:
            return await ctx.send(
                f"This server already has a newsboard at {newsboard.channel.mention}."
            )

        if guild := await self._has_newsboard(ctx.author.id):
            if await ctx.prompt(
                f"You have already set up a newsboard in **{str(guild)}**. Do you want to override it?"
            ):
                query = "DELETE FROM newsboard WHERE member_id = $1;"
                await self.bot.pool.execute(query, ctx.author.id)
                self.get_newsboard.invalidate(self, ctx.guild.id)
            else:
                return

        name = "overwatch-news"
        topic = "Latest Overwatch news."
        overwrites = {
            ctx.me: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, embed_links=True
            ),
            ctx.guild.default_role: discord.PermissionOverwrite(
                read_messages=True, send_messages=False, read_message_history=True
            ),
        }
        reason = f"{ctx.author} created a text channel #overwatch-news"

        try:
            channel = await ctx.guild.create_text_channel(
                name=name, overwrites=overwrites, topic=topic, reason=reason
            )
        except discord.Forbidden:
            return await ctx.send("I don't have permissions to create the channel.")
        except discord.HTTPException:
            return await ctx.send("Something bad happened. Please try again.")

        query = "INSERT INTO newsboard (id, server_id, member_id) VALUES ($1, $2, $3);"
        await self.bot.pool.execute(query, channel.id, ctx.guild.id, ctx.author.id)
        await ctx.send(f"Channel successfully created at {channel.mention}.")


async def setup(bot):
    await bot.add_cog(Overwatch(bot))
