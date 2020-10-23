import textwrap
import traceback

import discord
from discord.ext import commands


class Log(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @property
    def webhook(self):
        wh_id, wh_token = (
            self.bot.config.webhook["id"],
            self.bot.config.webhook["token"],
        )
        return discord.Webhook.partial(
            id=wh_id,
            token=wh_token,
            adapter=discord.AsyncWebhookAdapter(self.bot.session),
        )

    async def send_command_log(self, ctx):
        """Command logs on OverBot support server."""
        if self.bot.config.is_beta:
            return
        embed = discord.Embed(color=self.bot.color, timestamp=self.bot.timestamp)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Message", value=ctx.message.content)
        await self.webhook.send(embed=embed)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        await self.send_command_log(ctx)

    async def send_guild_log(self, embed, guild):
        """Sends information about a joined guild."""
        embed.title = guild.name
        if guild.icon:
            embed.set_thumbnail(url=guild.icon_url)
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Region", value=guild.region)
        embed.set_footer(text=f"ID: {guild.id}")
        await self.webhook.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if self.bot.config.is_beta:
            return
        embed = discord.Embed(color=0x4CA64C)
        await self.send_guild_log(embed, guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if self.bot.config.is_beta:
            return
        embed = discord.Embed(color=0xFF3232)
        await self.send_guild_log(embed, guild)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if self.bot.config.is_beta:
            return
        if not isinstance(
            error, (commands.CommandInvokeError, commands.ConversionError)
        ):
            return
        error = error.original
        if isinstance(error, (discord.Forbidden, discord.NotFound)):
            return
        embed = discord.Embed(title="Error", color=0xFF3232)
        embed.add_field(name="Command", value=ctx.command.qualified_name)
        embed.add_field(name="Author", value=ctx.author)
        fmt = f"Channel: {ctx.channel} (ID: {ctx.channel.id})"
        if ctx.guild:
            fmt = f"{fmt}\nGuild: {ctx.guild} (ID: {ctx.guild.id})"
        embed.add_field(name="Location", value=fmt, inline=False)
        embed.add_field(
            name="Content", value=textwrap.shorten(ctx.message.content, width=512)
        )
        exc = "".join(
            traceback.format_exception(
                type(error), error, error.__traceback__, chain=False
            )
        )
        embed.description = f"```py\n{exc}\n```"
        embed.timestamp = self.bot.timestamp
        channel = await self.bot.get_channel(self.bot.config.errors_channel)

        if not channel:
            return

        await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Log(bot))
