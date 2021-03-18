import textwrap
from datetime import datetime
from contextlib import suppress

import discord
from discord.ext import commands

from utils.scrape import get_overwatch_maps


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_log(self, color, message):
        if self.bot.debug:
            return

        embed = discord.Embed(color=color)
        embed.timestamp = self.bot.timestamp
        embed.title = message

        channel = self.bot.get_channel(self.bot.config.status_channel)

        if not channel:
            return

        await channel.send(embed=embed)

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

        await self.change_presence()
        await self.send_log(discord.Color.blue(), "Bot is online.")

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
                name="https://overbot.me",
                type=discord.ActivityType.playing,
            ),
            status=discord.Status.idle,
        )

    async def cache_heroes(self):
        url = self.bot.config.random["hero"]
        async with self.bot.session.get(url) as r:
            return await r.json()

    async def cache_maps(self):
        return await get_overwatch_maps()

    async def get_hero_names(self):
        return [str(h["key"]).lower() for h in self.bot.heroes]


def setup(bot):
    bot.add_cog(Events(bot))
