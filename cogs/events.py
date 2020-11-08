import time
import textwrap

import discord
from discord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
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

    @commands.Cog.listener()
    async def on_resumed(self):
        print("Connection resumed.")

    @commands.Cog.listener()
    async def on_connect(self):
        if not self.bot.start_time:
            self.bot.start_time = time.perf_counter()

    async def change_presence(self):
        await self.bot.wait_until_ready()
        await self.bot.change_presence(
            activity=discord.Activity(
                name=f"{self.bot.prefix}help",
                type=discord.ActivityType.playing,
            ),
            status=discord.Status.idle,
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.bot.pool.execute(
            'INSERT INTO server (id, "prefix") VALUES ($1, $2);',
            guild.id,
            self.bot.prefix,
        )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.bot.pool.execute("DELETE FROM server WHERE id=$1;", guild.id)


def setup(bot):
    bot.add_cog(Events(bot))
