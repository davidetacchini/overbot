import textwrap

from datetime import datetime
from contextlib import suppress

import discord

from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_log(self, text, color):
        if self.bot.debug:
            return

        embed = discord.Embed(color=color)
        embed.title = text
        embed.timestamp = datetime.utcnow()
        await self.bot.webhook.send(embed=embed)

    async def change_presence(self):
        await self.bot.wait_until_ready()
        game = discord.Game(f"{self.bot.prefix}help")
        await self.bot.change_presence(activity=game)

    async def send_guild_log(self, guild, embed):
        """Sends information about a joined guild."""
        embed.title = guild.name
        if guild.icon:
            embed.set_thumbnail(url=guild.icon_url)
        with suppress(AttributeError):
            embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Shard ID", value=guild.shard_id + 1)
        embed.set_footer(text=f"ID: {guild.id}")
        await self.bot.webhook.send(embed=embed)

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
            Using {discord.__name__} {discord.__version__}
            Running {self.bot.user.display_name} {self.bot.version} in {len(self.bot.guilds)} guilds
            -----------------
            """
            )
        )

        await self.change_presence()
        await self.send_log("Bot is online.", discord.Color.blue())

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        query = """INSERT INTO server (id, prefix)
                   VALUES ($1, $2)
                   ON CONFLICT (id) DO NOTHING;
                """
        await self.bot.pool.execute(query, guild.id, self.bot.prefix)

        if self.bot.debug:
            return

        embed = discord.Embed(color=discord.Color.green())
        await self.send_guild_log(guild, embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        with suppress(KeyError):
            del self.bot.prefixes[guild.id]
        await self.bot.pool.execute("DELETE FROM server WHERE id = $1;", guild.id)

        if self.bot.debug:
            return

        embed = discord.Embed(color=discord.Color.red())
        await self.send_guild_log(guild, embed)

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
    async def on_guild_channel_delete(self, channel):
        if not isinstance(channel, discord.TextChannel):
            return

        newsboard = await self.bot.get_cog("Overwatch").get_newsboard(channel.guild.id)
        if newsboard.channel_id != channel.id:
            return

        async with self.bot.pool.acquire(timeout=300.0) as conn:
            query = "DELETE FROM newsboard WHERE id = $1;"
            await conn.execute(query, channel.id)


def setup(bot):
    bot.add_cog(Events(bot))
