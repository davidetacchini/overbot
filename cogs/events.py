import textwrap
import traceback
from datetime import datetime
from contextlib import suppress

import discord
from discord.ext import commands

from utils.scrape import get_overwatch_maps


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
        await self.wehbhook.send(embed=embed)

    async def change_presence(self):
        await self.bot.wait_until_ready()
        game = discord.Game("https://overbot.me")
        await self.bot.change_presence(activity=game)

    async def cache_heroes(self):
        url = self.bot.config.random["hero"]
        async with self.bot.session.get(url) as r:
            return await r.json()

    async def cache_maps(self):
        return await get_overwatch_maps()

    async def get_hero_names(self):
        return [str(h["key"]).lower() for h in self.bot.heroes]

    async def cache_embed_colors(self):
        embed_colors = {}
        query = "SELECT id, embed_color FROM member WHERE embed_color <> NULL;"
        colors = await self.bot.pool.fetch(query)
        for member_id, color in colors:
            embed_colors[member_id] = color
        return embed_colors

    async def cache_premiums(self):
        query = """SELECT id
                   FROM member
                   WHERE member.premium = true
                   UNION
                   SELECT id
                   FROM server
                   WHERE server.premium = true;
                """
        ids = await self.bot.pool.fetch(query)
        # remove records, make a set of integers
        return {i["id"] for i in ids}

    async def send_guild_log(self, embed, guild):
        """Sends information about a joined guild."""
        embed.title = guild.name
        if guild.icon:
            embed.set_thumbnail(url=guild.icon_url)
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(name="Region", value=guild.region)
        embed.add_field(name="Shard ID", value=guild.shard_id + 1)
        embed.set_footer(text=f"ID: {guild.id}")
        await self.webhook.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        if not hasattr(self.bot, "uptime"):
            self.bot.uptime = datetime.utcnow()

        if not hasattr(self.bot, "total_lines"):
            self.bot.total_lines = 0
            self.bot.get_line_count()

        if not hasattr(self.bot, "heroes"):
            self.bot.heroes = await self.cache_heroes()

        if not hasattr(self.bot, "maps"):
            self.bot.maps = await self.cache_maps()

        if not hasattr(self.bot, "hero_names"):
            self.bot.hero_names = await self.get_hero_names()
            heroes = ["soldier", "soldier76", "wreckingball", "dva"]
            for hero in heroes:
                self.bot.hero_names.append(hero)

        if not hasattr(self.bot, "embed_colors"):
            self.bot.embed_colors = await self.cache_embed_colors()

        if not hasattr(self.bot, "premiums"):
            self.bot.premiums = await self.cache_premiums()

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
    async def on_disconnect(self):
        message = "Connection lost."
        await self.send_log(discord.Color.red(), message)

    @commands.Cog.listener()
    async def on_resumed(self):
        message = "Connection resumed."
        await self.send_log(discord.Color.green(), message)

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard_id):
        message = f"Shard {shard_id + 1} disconnected."
        await self.send_log(discord.Color.red(), message)

    @commands.Cog.listener()
    async def on_shard_connect(self, shard_id):
        message = f"Shard {shard_id + 1} connected."
        await self.send_log(discord.Color.green(), message)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.bot.pool.execute(
            "INSERT INTO server(id, prefix) VALUES($1, $2);",
            guild.id,
            self.bot.prefix,
        )

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

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if self.bot.debug:
            return

        if not isinstance(
            error, (commands.CommandInvokeError, commands.ConversionError)
        ):
            return

        error = error.original
        if isinstance(error, (discord.Forbidden, discord.NotFound)):
            return

        embed = discord.Embed(title="Error", color=discord.Color.red())
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
        await self.webhook.send(embed=embed)


def setup(bot):
    bot.add_cog(Events(bot))
