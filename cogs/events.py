import textwrap
from datetime import datetime
from contextlib import suppress

import discord
from discord.ext import commands
import os


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_log(self, color, message):
        if self.bot.debug:
            return

        embed = discord.Embed(color=color)
        embed.title = message

        channel = self.bot.get_channel(self.bot.config.status_channel)

        if not channel:
            return

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.send_log(discord.Color.blue(), "Bot is online.")
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

        if not hasattr(self.bot, "uptime"):
            self.bot.uptime = datetime.utcnow()

        if not hasattr(self.bot, "total_lines"):
            self.bot.total_lines = 0
            self.get_line_count()

        # caching all Overwatch heroes at startup. Used in
        # classes/converters.py to check if the entered hero exists.
        if not hasattr(self.bot, "heroes"):
            self.bot.heroes = await self.cache_heroes()

        await self.change_presence()

    @commands.Cog.listener()
    async def on_disconnect(self):
        message = "Connection lost."
        await self.send_log(discord.Color.red(), message)

    @commands.Cog.listener()
    async def on_resumed(self):
        message = "Connection resumed"
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

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        with suppress(KeyError):
            del self.bot.prefixes[guild.id]
        await self.bot.pool.execute("DELETE FROM server WHERE id = $1;", guild.id)

    async def change_presence(self):
        await self.bot.wait_until_ready()
        await self.bot.change_presence(
            activity=discord.Activity(
                name=f"{self.bot.prefix}help",
                type=discord.ActivityType.playing,
            ),
            status=discord.Status.idle,
        )

    def get_line_count(self):
        for root, dirs, files in os.walk(os.getcwd()):
            [dirs.remove(d) for d in list(dirs) if d == "env"]
            for name in files:
                if name.endswith(".py"):
                    with open(f"{root}/{name}") as f:
                        self.bot.total_lines += len(f.readlines())

    async def cache_heroes(self):
        url = self.bot.config.random["hero"]
        async with self.bot.session.get(url) as r:
            heroes = await r.json()
        return [str(h["key"]).lower() for h in heroes]


def setup(bot):
    bot.add_cog(Events(bot))
