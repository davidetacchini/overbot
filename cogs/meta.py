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


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["pong", "latency"])
    async def ping(self, ctx):
        """Displays the bot's current websocket latency and ACK."""
        embed = discord.Embed(color=self.bot.color)
        embed.title = "Pinging..."
        start = time.monotonic()
        msg = await ctx.send(embed=embed)
        embed.title = None
        ack = round((time.monotonic() - start) * 1000)
        embed.add_field(name="Latency", value=f"{self.bot.ping}ms")
        embed.add_field(name="ACK", value=f"{ack}ms")
        await msg.edit(embed=embed)

    @commands.command()
    async def uptime(self, ctx):
        """Shows how long the bot has been online."""
        await ctx.send(f"Uptime: {self.bot.get_uptime()}")

    @commands.command(aliases=["feed"])
    @commands.cooldown(1, 60.0, commands.BucketType.member)
    async def feedback(self, ctx, *, message: str):
        """Leave a feedback about the bot.

        You can leave a feedback once a minute"""
        channel = self.bot.get_channel(self.bot.config.feedback_channel)

        if not channel:
            return

        embed = discord.Embed(color=self.bot.color)
        embed.description = ctx.message.content
        embed.timestamp = ctx.message.created_at
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        await channel.send(embed=embed)
        await ctx.send(
            f"{str(ctx.author)}, your feedback has been successfully sent, thanks!"
        )

    @staticmethod
    def format_commit(commit):
        message, _, _ = commit.message.partition("\n")
        commit_tz = datetime.timezone(
            datetime.timedelta(minutes=commit.commit_time_offset)
        )
        commit_time = datetime.datetime.fromtimestamp(commit.commit_time).astimezone(
            commit_tz
        )

        offset = human_timedelta(
            commit_time.astimezone(datetime.timezone.utc).replace(tzinfo=None),
            accuracy=1,
        )
        return f"[`{commit.hex[:6]}`](https://github.com/davidetacchini/overbot/commit/{commit.hex}) {message} ({offset})"

    def get_latest_commits(self, count=3):
        repo = pygit2.Repository(".git")
        commits = list(
            itertools.islice(
                repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL), count
            )
        )
        return "\n".join(self.format_commit(c) for c in commits)

    # Inspired by Rapptz/RoboDanny
    # https://github.com/Rapptz/RoboDanny
    @commands.command(aliases=["info"])
    @commands.guild_only()
    async def about(self, ctx):
        """Displays the bot information."""
        async with ctx.typing():
            commits = self.get_latest_commits()
            embed = discord.Embed(color=self.bot.color)
            embed.title = "Official Website"
            embed.description = f"Latest Commits:\n{commits}"
            embed.url = self.bot.config.website
            embed.timestamp = self.bot.timestamp

            guild = await self.bot.fetch_guild(self.bot.config.support_server_id)
            owner = await guild.fetch_member(self.bot.config.owner_id)

            embed.set_author(
                name=str(owner),
                url=self.bot.config.github["profile"],
                icon_url=owner.avatar_url,
            )

            activity = (
                f"{psutil.cpu_percent()}% CPU\n" f"{psutil.virtual_memory()[2]}% RAM\n"
            )

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
                total_members += guild.member_count
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
            embed.add_field(name="Commands Runned", value=total_commands)
            embed.add_field(name="Lines of code", value=self.bot.total_lines)
            embed.add_field(name="Uptime", value=self.bot.get_uptime(brief=True))
            embed.set_footer(
                text=f"Made with discord.py v{discord.__version__}",
                icon_url=self.bot.config.python_logo,
            )
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Meta(bot))
