import time
import datetime
import platform
import itertools

import distro
import psutil
import pygit2
import discord

from discord.ext import commands

from utils.time import human_timedelta
from classes.help import CustomHelp


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.old_help_command = bot.help_command
        bot.help_command = CustomHelp()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self.old_help_command

    @commands.command()
    async def support(self, ctx):
        """Returns the official bot support server invite link."""
        await ctx.send(self.bot.config.support)

    @commands.command()
    async def vote(self, ctx):
        """Returns bot vote link."""
        await ctx.send(self.bot.config.vote)

    @commands.command()
    async def invite(self, ctx):
        """Returns bot invite link."""
        await ctx.send(self.bot.config.invite)

    @commands.command(aliases=["git"])
    async def github(self, ctx):
        """Returns the bot GitHub repository."""
        await ctx.send(self.bot.config.github["repo"])

    @commands.command(aliases=["pong", "latency"])
    async def ping(self, ctx):
        """Shows bot current websocket latency and ACK."""
        embed = discord.Embed(color=discord.Color.green())
        embed.title = "Pinging..."
        start = time.monotonic()
        msg = await ctx.send(embed=embed)
        embed.title = None
        ack = round((time.monotonic() - start) * 1000, 2)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000, 2)}ms")
        embed.add_field(name="ACK", value=f"{ack}ms")
        await msg.edit(embed=embed)

    @commands.command()
    async def uptime(self, ctx):
        """Shows how long the bot has been online."""
        await ctx.send(f"Uptime: {self.bot.get_uptime()}")

    @staticmethod
    def format_commit(commit):
        message, _, _ = commit.message.partition("\n")
        commit_tz = datetime.timezone(datetime.timedelta(minutes=commit.commit_time_offset))
        commit_time = datetime.datetime.fromtimestamp(commit.commit_time).astimezone(commit_tz)

        offset = human_timedelta(
            commit_time.astimezone(datetime.timezone.utc).replace(tzinfo=None),
            accuracy=1,
        )
        return f"[`{commit.hex[:6]}`](https://github.com/davidetacchini/overbot/commit/{commit.hex}) {message} ({offset})"

    def get_latest_commits(self, count=3):
        repo = pygit2.Repository(".git")
        commits = list(
            itertools.islice(repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL), count)
        )
        return "\n".join(self.format_commit(c) for c in commits)

    # inspired by https://github.com/Rapptz/RoboDanny
    @commands.command(aliases=["info"])
    @commands.guild_only()
    async def about(self, ctx):
        """Shows bot information."""
        async with ctx.typing():
            commits = self.get_latest_commits()
            embed = discord.Embed(color=self.bot.color(ctx.author.id))
            embed.title = "Official Website"
            embed.description = f"Latest Changes:\n{commits}"
            embed.url = self.bot.config.website
            embed.timestamp = ctx.message.created_at

            owner = await self.bot.get_or_fetch_member(self.bot.config.owner_id)

            embed.set_author(
                name=str(owner),
                url=self.bot.config.github["profile"],
                icon_url=owner.display_avatar,
            )

            activity = f"{psutil.cpu_percent()}% CPU\n" f"{psutil.virtual_memory()[2]}% RAM\n"

            os_name = distro.linux_distribution()[0]
            os_version = distro.linux_distribution()[1]
            host = f"{os_name} {os_version}\n" f"Python {platform.python_version()}"

            total_commands = await self.bot.total_commands()
            total_members = 0

            text = 0
            voice = 0
            guilds = 0
            for guild in self.bot.guilds:
                guilds += 1
                try:
                    total_members += guild.member_count
                except AttributeError:
                    pass
                for channel in guild.channels:
                    if isinstance(channel, discord.TextChannel):
                        text += 1
                    elif isinstance(channel, discord.VoiceChannel):
                        voice += 1

            embed.add_field(name="Process", value=activity)
            embed.add_field(name="Host", value=host)
            embed.add_field(
                name="Channels",
                value=f"{text + voice} total\n{text} text\n{voice} voice",
            )
            embed.add_field(name="Members", value=total_members)
            embed.add_field(name="Servers", value=len(self.bot.guilds))
            embed.add_field(
                name="Shards",
                value=f"{ctx.guild.shard_id + 1}/{self.bot.shard_count}",
            )
            embed.add_field(name="Commands Run", value=total_commands)
            embed.add_field(name="Lines of code", value=self.bot.total_lines)
            embed.add_field(name="Uptime", value=self.bot.get_uptime(brief=True))
            await ctx.send(embed=embed)

    async def get_weekly_top_guilds(self):
        query = """SELECT guild_id, COUNT(*) as commands
                   FROM command
                   WHERE created_at > now() - '1 week'::interval
                   GROUP BY guild_id
                   HAVING guild_id <> ALL($1::bigint[])
                   ORDER BY commands DESC
                   LIMIT 5;
                """
        return await self.bot.pool.fetch(query, self.bot.config.ignored_guilds)

    @commands.command()
    @commands.cooldown(1, 30.0, commands.BucketType.member)
    async def topweekly(self, ctx):
        """Shows bot's weekly most active servers.

        It is based on commands runned.

        You can use this command once every 30 seconds.
        """
        async with ctx.typing():
            guilds = await self.get_weekly_top_guilds()
            embed = discord.Embed(color=self.bot.color(ctx.author.id))
            embed.title = "Most Active Servers"
            embed.url = self.bot.config.website + "/#servers"
            embed.set_footer(text="Tracking command usage since - 03/31/2021")

            board = []
            for index, guild in enumerate(guilds, start=1):
                g = self.bot.get_guild(guild["guild_id"])
                if not g:
                    continue
                board.append(
                    f"{index}. **{str(g)}** ran a total of **{guild['commands']}** commands"
                )
            embed.description = "\n".join(board)
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Meta(bot))
