import io
import os
import re
import sys
import copy
import asyncio
import textwrap
import importlib
import traceback
from contextlib import suppress, redirect_stdout
from subprocess import PIPE

import discord
import aiosqlite
from discord.ext import commands


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

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

    # Source: https://github.com/Rapptz/RoboDanny
    _GIT_PULL_REGEX = re.compile(r"\s*(?P<filename>.+?)\s*\|\s*[0-9]+\s*[+-]+")

    def find_modules_from_git(self, output):
        files = self._GIT_PULL_REGEX.findall(output)
        ret = []
        for file in files:
            root, ext = os.path.splitext(file)
            if ext != ".py":
                continue

            if root.startswith("cogs/"):
                # A submodule is a directory inside the main cog directory for
                # my purposes
                ret.append((root.count("/") - 1, root.replace("/", ".")))

        # For reload order, the submodules should be reloaded first
        ret.sort(reverse=True)
        return ret

    def reload_or_load_extension(self, module):
        try:
            self.bot.reload_extension(module)
        except commands.ExtensionNotLoaded:
            self.bot.load_extension(module)

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
        mods_text = "\n".join(
            f"{index}. `{module}`" for index, (_, module) in enumerate(modules, start=1)
        )
        if not await ctx.prompt(
            f"This will update the following modules, are you sure?\n{mods_text}"
        ):
            return

        statuses = []
        for is_submodule, module in modules:
            if is_submodule:
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

        await ctx.send(
            "\n".join(f"{status}: `{module}`" for status, module in statuses)
        )

    @commands.command(hidden=True)
    async def rldconf(self, ctx):
        try:
            importlib.reload(self.bot.config)
        except Exception as exc:
            await ctx.send(f"""```prolog\n{type(exc).__name__}\n{exc}```""")
        else:
            await ctx.message.add_reaction("✅")

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
            "speedtest-cli --simple", stdin=None, stderr=PIPE, stdout=PIPE
        )
        ret = (await process.stdout.read()).decode("utf-8").strip()
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
            profiles = await self.bot.pool.fetch("SELECT * FROM profile;")
            prefixes = await self.bot.pool.fetch(
                "SELECT * FROM server WHERE prefix <> '-';"
            )
            guilds = await self.bot.pool.fetch("SELECT * FROM server;")
            total_commands = await self.bot.total_commands()

            embed = discord.Embed()
            embed.title = "Admin Panel"
            embed.add_field(name="Profiles", value=len(profiles))
            embed.add_field(name="Prefixes", value=len(prefixes))
            embed.add_field(name="Guilds", value=len(guilds))
            embed.add_field(name="Commands Used", value=total_commands)
            await ctx.send(embed=embed)
        except Exception as exc:
            await ctx.send(f"""```prolog\n{type(exc).__name__}\n{exc}```""")

    @commands.command(hidden=True)
    async def insert_guild(self, ctx):
        async with ctx.typing():
            for guild in self.bot.guilds:
                if not await self.bot.pool.fetchrow(
                    "SELECT * FROM server WHERE id=$1;", guild.id
                ):
                    await self.bot.pool.execute(
                        'INSERT INTO server (id, "prefix") VALUES ($1, $2);',
                        guild.id,
                        self.bot.prefix,
                    )
            await ctx.send("""```css\nGuilds successfully inserted.```""")

    @commands.command(hidden=True)
    async def insert_profiles(self, ctx):
        async with ctx.typing():
            async with aiosqlite.connect("main.sqlite") as conn:
                async with conn.execute("SELECT * FROM profiles") as pool:
                    rows = await pool.fetchall()
                    for row in rows:
                        await self.bot.pool.execute(
                            'INSERT INTO profile (id, "platform", "name") VALUES ($1, $2, $3)',
                            row[0],
                            row[1],
                            row[2],
                        )
            await ctx.send("""```css\nProfiles successfully inserted.```""")

    @commands.command(hidden=True)
    async def insert_prefixes(self, ctx):
        async with ctx.typing():
            async with aiosqlite.connect("main.sqlite") as conn:
                async with conn.execute("SELECT * FROM prefixes") as pool:
                    rows = await pool.fetchall()
                    for row in rows:
                        try:
                            await self.bot.pool.execute(
                                "UPDATE server SET prefix=$1 WHERE id=$2",
                                row[1],
                                int(row[0]),
                            )
                        except Exception as exc:
                            print(exc)
            await ctx.send("""```css\nPrefixes successfully updated.```""")


def setup(bot):
    bot.add_cog(Owner(bot))
