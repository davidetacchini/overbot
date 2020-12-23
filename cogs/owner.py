import io
import os
import re
import sys
import copy
import asyncio
import textwrap
import importlib
import traceback
import subprocess
from argparse import ArgumentParser
from contextlib import suppress, redirect_stdout

import discord
from discord.ext import commands


class Arguments(ArgumentParser):
    def error(self, message):
        raise RuntimeError(message)


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        if await self.bot.is_owner(ctx.author):
            return True
        raise commands.NotOwner()

    @commands.command(hidden=True)
    async def clr(self, ctx, amount: int = 1):
        """Remove the given amount of messages."""
        amount += 1
        await ctx.channel.purge(limit=amount)

    @commands.command(hidden=True)
    async def load(self, ctx, *, module: str):
        """Loads a module."""
        try:
            self.bot.load_extension(module)
        except Exception as exc:
            await ctx.send(f"""```prolog\n{type(exc).__name__}\n{exc}```""")
        else:
            await ctx.message.add_reaction("✅")

    @commands.command(hidden=True)
    async def unload(self, ctx, *, module: str):
        """Unloads a module."""
        try:
            self.bot.unload_extension(module)
        except Exception as exc:
            await ctx.send(f"""```prolog\n{type(exc).__name__}\n{exc}```""")
        else:
            await ctx.message.add_reaction("✅")

    @commands.group(name="reload", hidden=True, invoke_without_command=True)
    async def _reload(self, ctx, *, module):
        """Reloads a module."""
        try:
            self.bot.reload_extension(module)
        except Exception as exc:
            await ctx.send(f"""```prolog\n{type(exc).__name__}\n{exc}```""")
        else:
            await ctx.message.add_reaction("✅")

    @commands.command(hidden=True)
    async def rldconf(self, ctx):
        try:
            importlib.reload(self.bot.config)
        except Exception as exc:
            await ctx.send(f"""```prolog\n{type(exc).__name__}\n{exc}```""")
        else:
            await ctx.message.add_reaction("✅")

    async def run_process(self, command):
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

    def find_modules_from_git(self, output):
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

    def reload_or_load_extension(self, module):
        try:
            self.bot.reload_extension(module)
        except commands.ExtensionNotLoaded:
            self.bot.load_extension(module)

    # Source: https://github.com/Rapptz/RoboDanny
    @_reload.command(name="all", hidden=True)
    async def _reload_all(self, ctx):
        """Reloads all modules, while pulling from git."""

        async with ctx.typing():
            stdout, stderr = await self.run_process("git pull")

        # progress and stuff is redirected to stderr in git pull
        # however, things like "fast forward" and files
        # along with the text "already up-to-date" are in stdout

        if stdout.startswith("Already up-to-date."):
            return await ctx.send(stdout)

        modules = self.find_modules_from_git(stdout)
        updated_modules = "\n".join(
            f"{index}. `{module}`" for index, (_, module) in enumerate(modules, start=1)
        )
        if not await ctx.prompt(
            f"This will update the following modules, are you sure?\n{updated_modules}"
        ):
            return

        statuses = []
        for do_first, module in modules:
            if do_first:
                try:
                    actual_module = sys.modules[module]
                except KeyError:
                    statuses.append((ctx.tick(None), module))
                else:
                    try:
                        importlib.reload(actual_module)
                    except Exception:
                        statuses.append((ctx.tick(False), module))
                    else:
                        statuses.append((ctx.tick(True), module))
            else:
                try:
                    self.reload_or_load_extension(module)
                except commands.ExtensionError:
                    statuses.append((ctx.tick(False), module))
                else:
                    statuses.append((ctx.tick(True), module))

        await ctx.send("\n".join(f"{status} `{module}`" for status, module in statuses))
        # Update total line count since we have made changes.
        self.bot.total_lines = 0
        self.bot.get_line_count()

    @commands.command(aliases=["kys", "die"], hidden=True)
    async def shutdown(self, ctx):
        """Kills the bot session."""
        await ctx.send("Successfully gone offline.")
        await self.bot.logout()

    @commands.command(hidden=True)
    async def runas(self, ctx, member: discord.Member, *, command: str):
        """Run a command as if you were the user."""
        msg = copy.copy(ctx.message)
        msg._update(dict(channel=ctx.channel, content=ctx.prefix + command))
        msg.author = member
        new_ctx = await ctx.bot.get_context(msg)
        try:
            await ctx.bot.invoke(new_ctx)
        except Exception as exc:
            await ctx.send(f"""```prolog\n{type(exc).__name__}\n{exc}```""")

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])
        return content.strip("` \n")

    @commands.command(hidden=True)
    async def exc(self, ctx, *, body: str):
        """Evaluates a code."""
        env = {
            "bot": ctx.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as exc:
            return await ctx.send(f"```py\n{type(exc).__name__}: {exc}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            with suppress(discord.Forbidden):
                await ctx.message.add_reaction("✅")

            if not ret:
                if value:
                    await ctx.send(f"```py\n{value}\n```")
            else:
                await ctx.send(f"```py\n{value}{ret}\n```")

    @commands.command(hidden=True)
    async def speedtest(self, ctx):
        """Run a speedtest directly from Discord."""
        msg = await ctx.send("Running the speedtest...")
        process = await asyncio.create_subprocess_shell(
            "speedtest-cli --simple",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        ret = await process.stdout.read()
        ret = ret.decode("utf-8").strip()
        await msg.edit(content=f"""```prolog\n{ret}```""")

    @commands.command(hidden=True)
    async def sql(self, ctx, *, query: str):
        """Run a query."""
        query = self.cleanup_code(query)
        async with self.bot.pool.acquire() as conn:
            try:
                res = await conn.fetch(query)
            except Exception as exc:
                return await ctx.send(f"```prolog\n{exc}```")
            if res:
                await ctx.send(
                    f"""```asciidoc\nSuccessful query\n----------------\n\n{res}```"""
                )
            else:
                await ctx.send("There are no results.")

    @commands.command(hidden=True)
    async def admin(self, ctx):
        """Display an admin panel."""
        try:
            profiles = await self.bot.pool.fetchval("SELECT COUNT(*) FROM profile;")
            prefixes = self.bot.prefixes
            guilds = await self.bot.pool.fetchval("SELECT COUNT(*) FROM server;")
            ratings = await self.bot.pool.fetchval("SELECT COUNT(*) FROM rating;")

            total_commands = await self.bot.total_commands()
            played, won, lost, contribs = await self.bot.pool.fetchrow(
                "SELECT SUM(started), SUM(won), SUM(lost), SUM(contribs) FROM trivia;"
            )
            # Bot entries
            bot_entries = (
                ("Total profiles linked", profiles),
                ("Total prefixes set", len(prefixes)),
                ("Total profile ratings", ratings),
                ("Total guilds", guilds),
                ("Total commands runned", total_commands),
            )
            # Trivia entries
            trivia_entries = (
                ("Total games played", played),
                ("Total games won", won),
                ("Total games lost", lost),
                ("Total contributions", contribs),
            )

            embed = discord.Embed(color=ctx.author.color)
            embed.title = "Admin Panel"
            bot = []
            trivia = []

            for key, value in bot_entries:
                bot.append(f"{key}: **{value}**\n")

            for key, value in trivia_entries:
                trivia.append(f"{key}: **{value}**\n")

            embed.add_field(name="Bot", value="".join(bot))
            embed.add_field(name="Trivia", value="".join(trivia))

            await ctx.send(embed=embed)
        except Exception as exc:
            await ctx.send(f"""```prolog\n{type(exc).__name__}\n{exc}```""")

    def get_backup_arguments(self, args):
        import shlex

        parser = Arguments(add_help=False, allow_abbrev=False)
        parser.add_argument("--file", action="store_true")
        if args is not None:
            return parser.parse_args(shlex.split(args))
        else:
            return parser.parse_args([])

    @commands.command(hidden=True)
    async def backup(self, ctx, *, args: str = None):
        """Generate a backup file of the database."""
        msg = await ctx.send("Generating backup file...")

        try:
            args = self.get_backup_arguments(args)
        except RuntimeError as exc:
            return await ctx.send(exc)

        try:
            await asyncio.create_subprocess_shell(
                "pg_dump -U davide overbot > ../backup.sql",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await msg.add_reaction("✅")
        except Exception as exc:
            await msg.edit(content=f"""```prolog\n{exc}```""")

        if args.file:
            await asyncio.sleep(2)  # wait for the file to be created or updated.
            await ctx.send(file=discord.File("../backup.sql"), delete_after=15)


def setup(bot):
    bot.add_cog(Owner(bot))
