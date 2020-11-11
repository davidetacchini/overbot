import io
import copy
import asyncio
import textwrap
import traceback
from importlib import reload as il_reload
from contextlib import suppress, redirect_stdout
from subprocess import PIPE

import discord
import aiosqlite
from discord.ext import commands


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def clr(self, ctx, amount: int = 1):
        """Remove the given amount of messages."""
        amount += 1
        await ctx.channel.purge(limit=amount)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, *, cog: str):
        """Loads a module."""
        try:
            self.bot.load_extension(cog)
        except Exception as exc:
            await ctx.send(f"""```prolog\n{type(exc).__name__}\n{exc}```""")
        else:
            await ctx.message.add_reaction("✅")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, *, cog: str):
        """Unloads a module."""
        try:
            self.bot.unload_extension(cog)
        except Exception as exc:
            await ctx.send(f"""```prolog\n{type(exc).__name__}\n{exc}```""")
        else:
            await ctx.message.add_reaction("✅")

    @commands.command(name="reload", aliases=["rld"], hidden=True)
    @commands.is_owner()
    async def _reload(self, ctx, *, cog: str):
        """Reloads a module."""
        try:
            self.bot.reload_extension(cog)
        except Exception as exc:
            await ctx.send(f"""```prolog\n{type(exc).__name__}\n{exc}```""")
        else:
            await ctx.message.add_reaction("✅")

    @commands.command(hidden=True)
    async def rldconf(self, ctx):
        try:
            il_reload(self.bot.config)
        except Exception as exc:
            await ctx.send(f"""```prolog\n{type(exc).__name__}\n{exc}```""")
        else:
            await ctx.message.add_reaction("✅")

    @commands.command(aliases=["kys", "die"], hidden=True)
    @commands.is_owner()
    async def shutdown(self, ctx):
        """Kills the bot session."""
        await ctx.send("Successfully gone offline.")
        await self.bot.logout()

    @commands.command(hidden=True)
    @commands.is_owner()
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
    @commands.is_owner()
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
    @commands.is_owner()
    async def speedtest(self, ctx):
        """Run a speedtest directly from Discord."""
        msg = await ctx.send("Running the speedtest...")
        process = await asyncio.create_subprocess_shell(
            "speedtest-cli --simple", stdin=None, stderr=PIPE, stdout=PIPE
        )
        ret = (await process.stdout.read()).decode("utf-8").strip()
        await msg.edit(content=f"""```prolog\n{ret}```""")

    @commands.command(hidden=True)
    @commands.is_owner()
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
    @commands.is_owner()
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
    @commands.is_owner()
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
    @commands.is_owner()
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
    @commands.is_owner()
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
