from __future__ import annotations

import time
import datetime
import platform
import itertools

from typing import TYPE_CHECKING

import distro
import psutil
import pygit2
import discord

from discord import ui, app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from asyncpg import Record

    from bot import OverBot


class Meta(commands.Cog):
    def __init__(self, bot: OverBot) -> None:
        self.bot = bot

    @app_commands.command()
    async def help(self, interaction: discord.Interaction) -> None:
        """Shows help for OverBot"""
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.title = "OverBot Help"
        description = (
            "Click the button below to look at all the available "
            "Slash Commands and Context Menu ones."
        )
        embed.description = description

        view = ui.View()
        view.add_item(
            ui.Button(label="All available commands", url=self.bot.config.website + "/commands")
        )

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command()
    async def support(self, interaction: discord.Interaction) -> None:
        """Returns the official bot support server invite link"""
        await interaction.response.send_message(self.bot.config.support)

    @app_commands.command()
    async def ping(self, interaction: discord.Interaction) -> None:
        """Shows bot current websocket latency and ACK"""
        start = time.monotonic()
        await interaction.response.defer(thinking=True)
        ack = round((time.monotonic() - start) * 1000, 2)
        embed = discord.Embed(color=discord.Color.green())
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000, 2)}ms")
        embed.add_field(name="ACK", value=f"{ack}ms")
        await interaction.followup.send(embed=embed)

    @staticmethod
    def format_commit(commit: pygit2.Commit) -> str:
        message, _, _ = commit.message.partition("\n")
        commit_tz = datetime.timezone(datetime.timedelta(minutes=commit.commit_time_offset))
        commit_time = datetime.datetime.fromtimestamp(commit.commit_time).astimezone(commit_tz)

        offset = discord.utils.format_dt(commit_time.astimezone(datetime.timezone.utc), "R")
        return f"[`{commit.hex[:6]}`](https://github.com/davidetacchini/overbot/commit/{commit.hex}) {message} ({offset})"

    def get_latest_commits(self, count: int = 3) -> str:
        repo = pygit2.Repository(".git")
        commits = list(
            itertools.islice(repo.walk(repo.head.target, pygit2.GIT_SORT_TOPOLOGICAL), count)
        )
        return "\n".join(self.format_commit(c) for c in commits)

    # inspired by https://github.com/Rapptz/RoboDanny
    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: i.user.id)
    async def about(self, interaction: discord.Interaction) -> None:
        """Shows bot related information and useful links"""
        commits = self.get_latest_commits()

        view = ui.View()
        view.add_item(ui.Button(label="Website", url=self.bot.config.website))
        view.add_item(ui.Button(label="GitHub", url=self.bot.config.github["repo"]))
        view.add_item(ui.Button(label="Invite", url=self.bot.config.invite))
        view.add_item(ui.Button(label="Vote", url=self.bot.config.vote))

        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.description = f"Latest Changes:\n{commits}"

        embed.set_author(
            name=str(self.bot.owner),
            url=self.bot.config.github["profile"],
            icon_url=self.bot.owner.display_avatar.url,
        )

        activity = f"{psutil.cpu_percent()}% CPU\n" f"{psutil.virtual_memory()[2]}% RAM\n"

        os_name = distro.linux_distribution()[0]
        os_version = distro.linux_distribution()[1]
        py_version = platform.python_version()
        pg_version = await self.bot.get_pg_version()
        host = f"{os_name} {os_version}\n" f"Python {py_version}\n" f"PostgreSQL {pg_version}"

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
            name="Shards", value=f"{interaction.guild.shard_id + 1}/{self.bot.shard_count}"
        )
        embed.add_field(name="Commands Run", value=total_commands)
        embed.add_field(name="Lines of code", value=self.bot.sloc)
        embed.add_field(name="Uptime", value=self.bot.get_uptime(brief=True))
        embed.set_footer(
            text=f"{self.bot.user.name} {self.bot.version}", icon_url=self.bot.user.avatar
        )
        await interaction.response.send_message(embed=embed, view=view)

    async def get_weekly_top_guilds(self, bot: OverBot) -> list[Record]:
        query = """SELECT guild_id, COUNT(*) as commands
                   FROM command
                   WHERE created_at > now() - '1 week'::interval
                   GROUP BY guild_id
                   HAVING guild_id <> ALL($1::bigint[])
                   ORDER BY commands DESC
                   LIMIT 5;
                """
        return await bot.pool.fetch(query, self.bot.config.ignored_guilds)

    @app_commands.command()
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: i.user.id)
    async def topweekly(self, interaction: discord.Interaction) -> None:
        """Shows bot's weekly most active servers

        Based on commands runned
        """
        await interaction.response.defer(thinking=True)
        guilds = await self.get_weekly_top_guilds(self.bot)
        embed = discord.Embed(color=self.bot.color(interaction.user.id))
        embed.title = "Most Active Servers"
        embed.url = self.bot.config.website + "/#servers"
        embed.set_footer(text="Tracking command usage since - 03/31/2021")

        board = []
        for index, guild in enumerate(guilds, start=1):
            g = self.bot.get_guild(guild["guild_id"])
            if not g:
                continue
            board.append(f"{index}. **{str(g)}** ran a total of **{guild['commands']}** commands")
        embed.description = "\n".join(board)
        await interaction.followup.send(embed=embed)


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Meta(bot))
