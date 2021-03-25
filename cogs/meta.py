import time
import datetime
import platform
import itertools

import distro
import psutil
import pygit2
import discord
from discord.ext import commands

from utils.i18n import _, locale
from utils.time import human_timedelta


class Meta(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["pong", "latency"])
    @locale
    async def ping(self, ctx):
        _("""Displays the bot's current websocket latency and ACK.""")
        embed = discord.Embed(color=discord.Color.green())
        embed.title = _("Pinging...")
        start = time.monotonic()
        msg = await ctx.send(embed=embed)
        embed.title = None
        ack = round((time.monotonic() - start) * 1000, 2)
        embed.add_field(
            name=_("Latency"), value=f"{round(self.bot.latency * 1000, 2)}ms"
        )
        embed.add_field(name="ACK", value=f"{ack}ms")
        await msg.edit(embed=embed)

    @commands.command()
    @locale
    async def uptime(self, ctx):
        _("""Shows how long the bot has been online.""")
        await ctx.send(f"Uptime: {self.bot.get_uptime()}")

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
    @locale
    async def about(self, ctx):
        _("""Displays the bot information.""")
        async with ctx.typing():
            commits = self.get_latest_commits()
            embed = discord.Embed(color=self.bot.get_color(ctx.author.id))
            embed.title = _("Official Website")
            embed.description = _("Latest Changes:\n{commits}").format(commits=commits)
            embed.url = self.bot.config.website
            embed.timestamp = ctx.message.created_at

            owner = await self.bot.get_or_fetch_member(self.bot.config.owner_id)

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
                try:
                    total_members += guild.member_count
                except AttributeError:
                    pass
                for channel in guild.channels:
                    if isinstance(channel, discord.TextChannel):
                        text += 1
                    elif isinstance(channel, discord.VoiceChannel):
                        voice += 1

            embed.add_field(name=_("Process"), value=activity)
            embed.add_field(name=_("Host"), value=host)
            embed.add_field(
                name=_("Channels"),
                value=_(
                    "{total} total\n{text} text\n{voice} voice",
                ).format(total=text + voice, text=text, voice=voice),
            )
            embed.add_field(name=_("Members"), value=total_members)
            embed.add_field(name=_("Servers"), value=len(self.bot.guilds))
            embed.add_field(
                name=_("Shards"),
                value=f"{ctx.guild.shard_id + 1}/{self.bot.shard_count}",
            )
            embed.add_field(name=_("Commands Run"), value=total_commands)
            embed.add_field(name=_("Lines of code"), value=self.bot.total_lines)
            embed.add_field(name=_("Uptime"), value=self.bot.get_uptime(brief=True))
            embed.set_footer(
                text=_("Made with discord.py v{discord_version}").format(
                    discord_version=discord.__version__
                ),
                icon_url=self.bot.config.python_logo,
            )
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Meta(bot))
