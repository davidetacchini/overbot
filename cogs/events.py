import textwrap
import traceback
from datetime import datetime
from contextlib import suppress

import discord
from discord.ext import menus, commands


class Events(commands.Cog):
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

    async def send_log(self, color, message):
        if self.bot.debug:
            return

        embed = discord.Embed(color=color)
        embed.title = message
        embed.timestamp = self.bot.timestamp
        await self.webhook.send(embed=embed)

    async def change_presence(self):
        await self.bot.wait_until_ready()
        game = discord.Game(f"{self.bot.prefix}help")
        await self.bot.change_presence(activity=game)

    async def send_guild_log(self, embed, guild):
        """Sends information about a joined guild."""
        embed.title = guild.name
        if guild.icon:
            embed.set_thumbnail(url=guild.icon_url)
        try:
            embed.add_field(name="Members", value=guild.member_count)
        except AttributeError:
            pass
        embed.add_field(name="Region", value=guild.region)
        embed.add_field(name="Shard ID", value=guild.shard_id + 1)
        embed.set_footer(text=f"ID: {guild.id}")
        await self.webhook.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        if not hasattr(self.bot, "uptime"):
            self.bot.uptime = datetime.utcnow()

        print(
            textwrap.dedent(
                f"""
            -----------------
            Connection established.
            Logged in as {self.bot.user.display_name} - {self.bot.user.id}
            Using discord.py {discord.__version__}
            Running {self.bot.user.display_name} {self.bot.version} in {len(self.bot.guilds)} guilds
            -----------------
            """
            )
        )

        await self.change_presence()
        await self.send_log(discord.Color.blue(), "Bot is online.")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        query = """INSERT INTO server(id, prefix)
                   VALUES($1, $2)
                   ON CONFLICT (id) DO NOTHING;
                """
        await self.bot.pool.execute(query, guild.id, self.bot.prefix)

        if self.bot.debug:
            return

        embed = discord.Embed(color=discord.Color.green())
        await self.send_guild_log(embed, guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        with suppress(KeyError):
            del self.bot.prefixes[guild.id]
        await self.bot.pool.execute("DELETE FROM server WHERE id = $1;", guild.id)

        if self.bot.debug:
            return

        embed = discord.Embed(color=discord.Color.red())
        await self.send_guild_log(embed, guild)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        query = """INSERT INTO member (id)
                   VALUES ($1)
                   ON CONFLICT (id) DO NOTHING;
                """
        await self.bot.pool.execute(query, ctx.author.id)

        if ctx.guild:
            query = """INSERT INTO server (id, prefix)
                       VALUES ($1, $2)
                       ON CONFLICT (id) DO NOTHING;
                    """
            await self.bot.pool.execute(query, ctx.guild.id, self.bot.prefix)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if self.bot.debug:
            return

        if not isinstance(
            error, (commands.CommandInvokeError, commands.ConversionError)
        ):
            return

        error = error.original
        if isinstance(error, (discord.Forbidden, discord.NotFound, menus.MenuError)):
            return

        embed = discord.Embed(title="Error", color=discord.Color.red())
        embed.add_field(name="Command", value=ctx.command.qualified_name)
        embed.add_field(name="Author", value=ctx.author)
        if ctx.guild:
            fmt = f"Guild: {ctx.guild} (ID: {ctx.guild.id})"
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
        embed.timestamp = ctx.message.created_at
        await self.webhook.send(embed=embed)


def setup(bot):
    bot.add_cog(Events(bot))
