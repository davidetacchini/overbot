from __future__ import annotations

import asyncio
import importlib
import io
import logging
import os
import re
import subprocess
import sys
import textwrap
import traceback
from contextlib import redirect_stdout
from enum import Enum
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import is_owner
from utils.helpers import module_autocomplete
from utils.scrape import get_overwatch_news_from_ids

if TYPE_CHECKING:
    from bot import OverBot


log = logging.getLogger(__name__)


class Target(Enum):
    USER = 1
    SERVER = 2


class Owner(commands.Cog):
    def __init__(self, bot: OverBot):
        self.bot = bot

    reload = app_commands.Group(name="reload", description="Reloads modules or the config file.")
    sql = app_commands.Group(name="sql", description="Executes SQL queries.")
    sync = app_commands.Group(name="sync", description="Sync stuff.")

    @app_commands.command()
    @is_owner()
    async def clear(self, interaction: discord.Interaction, amount: int = 1) -> None:
        """Remove the given amount of messages"""
        await interaction.response.defer()
        amount += 1
        if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.purge(limit=amount)

    @app_commands.command()
    @is_owner()
    async def load(self, interaction: discord.Interaction, *, module: str) -> None:
        """Loads a module"""
        await interaction.response.defer(thinking=True)
        try:
            await self.bot.load_extension(module)
        except Exception as e:
            await interaction.followup.send(f"""```prolog\n{type(e).__name__}\n{e}```""")
        else:
            await interaction.followup.send(f"Module {module} successfully loaded.")

    @app_commands.command()
    @app_commands.autocomplete(module=module_autocomplete)
    @is_owner()
    async def unload(self, interaction: discord.Interaction, *, module: str) -> None:
        """Unloads a module"""
        await interaction.response.defer(thinking=True)
        try:
            await self.bot.unload_extension(module)
        except Exception as e:
            await interaction.followup.send(f"""```prolog\n{type(e).__name__}\n{e}```""")
        else:
            await interaction.followup.send(f"Module {module} successfully unloaded.")

    @reload.command()
    @app_commands.autocomplete(module=module_autocomplete)
    @is_owner()
    async def module(self, interaction: discord.Interaction, *, module: str) -> None:
        """Reloads a module"""
        await interaction.response.defer(thinking=True)
        try:
            await self.bot.reload_extension(module)
        except Exception as e:
            await interaction.followup.send(f"""```prolog\n{type(e).__name__}\n{e}```""")
        else:
            await interaction.followup.send(f"Module {module} successfully reloaded.")

    @reload.command()
    @is_owner()
    async def config(self, interaction: discord.Interaction) -> None:
        """Reloads the configuration file"""
        await interaction.response.defer(thinking=True)
        try:
            importlib.reload(self.bot.config)
        except Exception as e:
            await interaction.followup.send(f"""```prolog\n{type(e).__name__}\n{e}```""")
        else:
            await interaction.followup.send("Configuration successfully reloaded.")

    # Credits to https://github.com/Rapptz/RoboDanny
    @reload.command()
    @is_owner()
    async def modules(self, interaction: discord.Interaction) -> None:
        """Reloads all modules, while pulling from git"""
        await interaction.response.defer(thinking=True)
        stdout, _ = await self.run_process("git pull")

        # progress and stuff is redirected to stderr in git pull
        # however, things like "fast forward" and files
        # along with the text "Already up to date" are in stdout

        if stdout.startswith("Already up to date."):
            await interaction.followup.send(stdout)
            return

        modules = self.find_modules_from_git(stdout)
        updated_modules = "\n".join(
            f"{index}. `{module}`" for index, (_, module) in enumerate(modules, start=1)
        )
        message = f"This will update the following modules?\n{updated_modules}"
        if not await self.bot.prompt(interaction, message):
            return

        statuses = []
        for do_first, module in modules:
            if do_first:
                try:
                    actual_module = sys.modules[module]
                except KeyError:
                    statuses.append((self.bot.tick(None), module))
                else:
                    try:
                        importlib.reload(actual_module)
                    except Exception:
                        statuses.append((self.bot.tick(False), module))
                    else:
                        statuses.append((self.bot.tick(True), module))
            else:
                try:
                    await self.reload_or_load_extension(module)
                except commands.ExtensionError:
                    statuses.append((self.bot.tick(False), module))
                else:
                    statuses.append((self.bot.tick(True), module))

        await interaction.followup.send(
            "\n".join(f"{status} `{module}`" for status, module in statuses)
        )
        # update sloc because it most likely has been changed
        self.bot.sloc = 0
        self.bot.compute_sloc()

    async def run_process(self, command: str) -> list:
        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    _GIT_PULL_REGEX = re.compile(r"\s*(?P<filename>.+?)\s*\|\s*[0-9]+\s*[+-]+")

    def find_modules_from_git(self, output: str) -> list[tuple[bool, str]]:
        files = self._GIT_PULL_REGEX.findall(output)
        ret = []
        for file in files:
            root, ext = os.path.splitext(file)
            if ext != ".py":
                continue

            if root.startswith("cogs/"):
                ret.append((False, root.replace("/", ".")))

            if root.startswith("utils/") or root.startswith("classes/"):
                ret.append((True, root.replace("/", ".")))

        # Reload 'utils' and 'classes' modules before reloading 'cogs' ones.
        ret.sort(reverse=True)
        return ret

    async def reload_or_load_extension(self, module: str) -> None:
        try:
            await self.bot.reload_extension(module)
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension(module)

    @app_commands.command()
    @is_owner()
    async def shutdown(self, interaction: discord.Interaction) -> None:
        """Kills the bot session"""
        await interaction.response.send_message("Going offline.")
        await self.bot.close()

    @app_commands.command()
    @is_owner()
    async def exec(self, interaction: discord.Interaction, code: str) -> None:
        """Evaluates a piece of code"""
        env = {
            "bot": self.bot,
            "interaction": interaction,
            "channel": interaction.channel,
            "author": interaction.user,
            "guild": interaction.guild,
            "message": interaction.message,
        }

        env.update(globals())

        stdout = io.StringIO()

        body = code or ""
        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            await interaction.response.send_message(f"```py\n{type(e).__name__}: {e}\n```")
            return

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await interaction.response.send_message(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            if not ret:
                if value:
                    await interaction.response.send_message(f"```py\n{value}\n```")
            else:
                await interaction.response.send_message(f"```py\n{value}{ret}\n```")

    @app_commands.command()
    @is_owner()
    async def speedtest(self, interaction: discord.Interaction) -> None:
        """Run a speedtest directly from Discord"""
        await interaction.response.send_message("Running the speedtest...")
        process = await asyncio.create_subprocess_shell(
            "speedtest-cli --simple",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        ret = "Nothing..."
        if process.stdout:
            ret = (await process.stdout.read()).decode("utf-8").strip()
        await interaction.edit_original_response(content=f"""```prolog\n{ret}```""")

    @sql.command()
    @is_owner()
    async def execute(self, interaction: discord.Interaction, query: str) -> None:
        """INSERT, UPDATE or DELETE from database"""
        async with self.bot.pool.acquire() as conn:
            try:
                await conn.execute(query)
            except Exception as e:
                await interaction.response.send_message(f"```prolog\n{e}```")
            else:
                await interaction.response.send_message("Successful query.")

    @sql.command()
    @is_owner()
    async def fetch(self, interaction: discord.Interaction, query: str) -> None:
        """Fetch data from database"""
        async with self.bot.pool.acquire() as conn:
            try:
                res = await conn.fetch(query)
            except Exception as e:
                await interaction.response.send_message(f"```prolog\n{e}```")
                return
            if res:
                await interaction.response.send_message(
                    f"""```asciidoc\nSuccessful query\n----------------\n\n{res}```"""
                )
            else:
                await interaction.response.send_message("There are no results.")

    @app_commands.command()
    @is_owner()
    async def admin(self, interaction: discord.Interaction) -> None:
        """Display an admin panel"""
        async with self.bot.pool.acquire() as conn:
            profiles = await conn.fetchval("SELECT COUNT(*) FROM profile;")
            guilds = await conn.fetchval("SELECT COUNT(*) FROM server;")
            members = await conn.fetchval("SELECT COUNT(*) from member;")
            ratings = await conn.fetchval("SELECT COUNT(*) FROM rating;")
            played, won, lost = await conn.fetchrow(
                "SELECT SUM(started), SUM(won), SUM(lost) FROM trivia;"
            )

        total_commands = await self.bot.total_commands()
        bot_entries = (
            ("Total profiles linked", profiles),
            ("Total profile ratings", ratings),
            ("Total guilds", guilds),
            ("Total members", members),
            ("Total commands runned", total_commands),
        )
        trivia_entries = (
            ("Total games played", played),
            ("Total games won", won),
            ("Total games lost", lost),
        )

        embed = discord.Embed(color=self.bot.color())
        embed.title = "Admin Panel"
        bot = []
        trivia = []

        for key, value in bot_entries:
            bot.append(f"{key}: **{value}**")

        for key, value in trivia_entries:
            trivia.append(f"{key}: **{value}**")

        embed.add_field(name="Bot", value="\n".join(bot))
        embed.add_field(name="Trivia", value="\n".join(trivia))

        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    @is_owner()
    async def backup(self, interaction: discord.Interaction) -> None:
        """Backup database"""
        await interaction.response.send_message("Generating backup file...", ephemeral=True)

        try:
            await asyncio.create_subprocess_shell(
                "pg_dump -h localhost -U davide -d overbot --data-only > ../backup.sql",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await interaction.edit_original_response(content="Backup file successfully generated.")
        except Exception as e:
            await interaction.edit_original_response(content=f"""```prolog\n{e}```""")

    @sync.command()
    @is_owner()
    async def guilds(self, interaction: discord.Interaction):
        """Sync guilds with database.

        If a guild quit when the bot was offline, then remove it from database.
        If a guild joined when the bot was offline, then add it to database.
        """
        await interaction.response.send_message("Checking for guilds to remove...", ephemeral=True)
        db_guilds = await self.bot.pool.fetch("SELECT id FROM server;")
        db_guild_ids = [g["id"] for g in db_guilds]
        actual_guild_ids = [g.id for g in self.bot.guilds]
        ret = []

        # DELETE
        total = 0
        for guild_id in db_guild_ids:
            if guild_id not in actual_guild_ids:
                total += 1
                await self.bot.pool.execute("DELETE FROM server WHERE id = $1;", guild_id)
        ret.append(f"{total} guild(s) removed.")

        await interaction.edit_original_response(content="Checking for guilds to insert...")

        # INSERT
        total = 0
        for guild_id in actual_guild_ids:
            if guild_id not in db_guild_ids:
                total += 1
                query = """INSERT INTO server (id) VALUES ($1)
                           ON CONFLICT (id) DO NOTHING;
                        """
                await self.bot.pool.execute(query, guild_id)
        ret.append(f"{total} guild(s) inserted.")
        await interaction.followup.send("\n".join(ret), ephemeral=True)

    @sync.command()
    @is_owner()
    async def news(self, interaction: discord.Interaction, raw_ids: str) -> None:
        """Send unsent news to server newsboards."""
        await interaction.response.defer(thinking=True)

        ids = raw_ids.split(",")

        try:
            news = await get_overwatch_news_from_ids(ids, session=self.bot.session)
        except Exception as e:
            log.exception(e)
            await interaction.followup.send(f"```prolog\n{e}```")
            return

        records = await self.bot.pool.fetch("SELECT id FROM newsboard;")
        for n in news:
            embed = discord.Embed()
            embed.title = n["title"]
            embed.url = n["link"]
            embed.set_author(name="Blizzard Entertainment")
            embed.set_image(url=n["thumbnail"])
            embed.set_footer(text=n["date"])

            for record in records:
                channel_id = record["id"]
                channel = self.bot.get_channel(channel_id)
                if not channel or not isinstance(channel, discord.TextChannel):
                    continue
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    continue

        message = f"**{len(ids)}** news successfully sent to **{len(records)}** channels."
        log.info(message)
        await interaction.followup.send(message)

    @app_commands.command()
    @is_owner()
    async def addpremium(
        self, interaction: discord.Interaction, *, target: Target, target_id: str
    ) -> None:
        """Set Premium for a given target."""
        await interaction.response.defer(thinking=True)

        if target is Target.USER:
            query = """INSERT INTO member (id, premium)
                       VALUES ($1, true)
                       ON CONFLICT (id) DO
                       UPDATE SET premium = true;
                    """
        elif target is Target.SERVER:
            query = """INSERT INTO server (id, premium)
                       VALUES ($1, true)
                       ON CONFLICT (id) DO
                       UPDATE SET premium = true;
                    """
        try:
            await self.bot.pool.execute(query, int(target_id))
        except Exception:
            message = f"Cannot set premium for **{target_id}**."
            log.exception(message)
        else:
            self.bot.premiums.add(int(target_id))
            message = f"Premium set for **{target_id}**."
            log.info(message)
        await interaction.followup.send(message)

    @app_commands.command()
    @is_owner()
    async def delpremium(
        self, interaction: discord.Interaction, *, target: Target, target_id: str
    ) -> None:
        """Delete Premium for a given target."""
        await interaction.response.defer(thinking=True)

        if target is Target.USER:
            query = "UPDATE member SET premium = false WHERE id = $1;"
        elif target is Target.SERVER:
            query = "UPDATE server SET premium = false WHERE id = $1;"
        try:
            await self.bot.pool.execute(query, int(target_id))
        except Exception:
            message = f"Cannot remove premium for **{target_id}**."
            log.exception(message)
        else:
            self.bot.premiums.remove(int(target_id))
            message = f"Premium removed for **{target_id}**."
            log.info(message)
        await interaction.followup.send(message)


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Owner(bot), guild=bot.TEST_GUILD)
