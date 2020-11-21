"""MIT License.

Copyright (c) 2019-2020 Davide Tacchini

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import os
import re
import asyncio
import datetime
from contextlib import suppress

import asyncpg
import discord
import pygicord
from bs4 import BeautifulSoup
from aiohttp import ClientSession
from termcolor import colored
from discord.ext import commands

import config
from utils import data
from utils.time import human_timedelta
from classes.context import Context

try:
    import uvloop
except ImportError:
    pass
else:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


class Bot(commands.AutoShardedBot):
    """Custom bot class for OverBot."""

    def __init__(self, **kwargs):
        super().__init__(command_prefix=config.default_prefix, **kwargs)
        self.remove_command("help")
        self.config = config
        self.total_lines = 0
        self.prefixes = {}
        self.get_line_count()

        self.paginator = pygicord
        self.data = data

    def __repr__(self):
        return "<Bot>"

    @property
    def timestamp(self):
        return datetime.datetime.utcnow()

    @property
    def ping(self):
        return round(self.latency * 1000)

    @property
    def prefix(self):
        return config.default_prefix

    @property
    def version(self):
        return config.version

    @property
    def color(self):
        return config.main_color

    @property
    def is_beta(self):
        return config.is_beta

    def get_uptime(self, *, brief=False):
        return human_timedelta(self.uptime, accuracy=None, brief=brief, suffix=False)

    async def total_commands(self):
        return await self.pool.fetchval("SELECT total FROM command;")

    def get_line_count(self):
        for root, dirs, files in os.walk(os.getcwd()):
            [dirs.remove(d) for d in list(dirs) if d == "env"]
            for name in files:
                if name.endswith(".py"):
                    with open(f"{root}/{name}") as f:
                        self.total_lines += len(f.readlines())

    async def on_command(self, ctx):
        await self.pool.execute("UPDATE command SET total=total+1 WHERE id=1;")
        if ctx.guild:
            await self.pool.execute(
                "UPDATE server SET commands_runned=commands_runned+1 WHERE id=$1;",
                ctx.guild.id,
            )
        if not await self.pool.fetchrow(
            "SELECT * FROM member WHERE id=$1;", ctx.author.id
        ):
            await self.pool.execute(
                "INSERT INTO member (id) VALUES ($1);", ctx.author.id
            )
        await self.pool.execute(
            "UPDATE member SET commands_runned=commands_runned+1 WHERE id=$1;",
            ctx.author.id,
        )

    async def on_message(self, message):
        if not self.is_ready():
            return
        await self.process_commands(message)

    async def _get_prefix(self, bot, message):
        if not message.guild:
            return self.prefix
        try:
            return commands.when_mentioned_or(self.prefixes[message.guild.id])(
                self, message
            )
        except KeyError:
            return commands.when_mentioned_or(self.prefix)(self, message)

    def clean_prefix(self, ctx):
        user = ctx.guild.me if ctx.guild else ctx.bot.user
        pattern = re.compile(r"<@!?%s>" % user.id)
        return pattern.sub("@%s" % user.display_name.replace("\\", r"\\"), ctx.prefix)

    def loading_embed(self):
        embed = discord.Embed(color=discord.Color.dark_theme())
        embed.set_author(name="Fetching...", icon_url=self.config.loading_gif)
        return embed

    async def cleanup(self, message):
        with suppress(discord.HTTPException, discord.Forbidden):
            await message.delete()

    def get_subcommands(self, ctx, command):
        subcommands = getattr(command, "commands")
        embed = discord.Embed(color=self.color)
        embed.title = f"{str(command).capitalize()} Commands"
        embed.description = f'Use "{ctx.prefix}help {str(command)} [command]" for more information on a command'
        embed.set_footer(
            text="Replace [command] with one of the commands listed above."
        )
        sub = [f"`{subcommand.name}`" for subcommand in subcommands]
        value = ", ".join(sub)
        embed.add_field(name="Commands Available", value=value)
        embed.add_field(
            name="Usage",
            value=f"{ctx.prefix}{str(command)} [command]",
            inline=False,
        )
        return embed

    def embed_exception(self, exc):
        """Returns a custom embed for exceptions."""
        embed = discord.Embed(color=0xFF3232)
        embed.title = "An unknown error occured."
        embed.description = (
            "Please report the following error to the developer"
            " by joning the support server at https://discord.gg/eZU69EV"
        )
        embed.add_field(name=type(exc).__name__, value=exc)
        return embed

    async def get_overwatch_status(self):
        async with self.session.get(self.config.overwatch["status"]) as r:
            content = await r.read()
        page = BeautifulSoup(content, features="html.parser")
        return page.find(class_="entry-title").get_text()

    async def get_overwatch_news(self, a):
        async with self.session.get(self.config.overwatch["news"]) as r:
            content = await r.read()
        page = BeautifulSoup(content, features="html.parser")
        news = page.find("section", {"class", "NewsHeader-featured"})
        titles = [x.get_text() for x in news.find_all("h1", {"class": "Card-title"})][
            :a
        ]
        links = ["https://playoverwatch.com" + x["href"] for x in news][:a]
        imgs = [
            x["style"].split("url(")[1][:-1]
            for x in news.find_all("div", {"class", "Card-thumbnail"})
        ][:a]
        dates = [x.get_text() for x in news.find_all("p", {"class": "Card-date"})][:a]
        return titles, links, imgs, dates

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=Context)

    async def start(self, *args, **kwargs):
        self.session = ClientSession(loop=self.loop)
        self.pool = await asyncpg.create_pool(
            **self.config.database, max_size=20, command_timeout=60.0
        )
        # Caching prefixes at startup
        rows = await self.pool.fetch('SELECT id, "prefix" FROM server;')
        for row in rows:
            if row["prefix"] != self.prefix:
                self.prefixes[row["id"]] = row["prefix"]
        self.command_prefix = self._get_prefix
        for extension in os.listdir("cogs"):
            if extension.endswith(".py"):
                try:
                    self.load_extension(f"cogs.{extension[:-3]}")
                except Exception as exc:
                    print(
                        f"[{colored('ERROR', 'red')}] {extension:20} failed its loading!\n[{exc}]"
                    )
                else:
                    print(
                        f"[{colored('OK', 'green')}] {extension:20} successfully loaded"
                    )
        await super().start(config.token, reconnect=True)

    async def logout(self):
        await self.session.close()
        await self.pool.close()
        await super().logout()


def main():
    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True
    intents.reactions = True
    intents.messages = True

    bot = Bot(
        case_insensitive=True,
        activity=discord.Game(name="Starting..."),
        status=discord.Status.dnd,
        intents=intents,
        chunk_guilds_at_startup=False,
        guild_ready_timeout=5,
    )
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(bot.start())
    except KeyboardInterrupt:
        loop.run_until_complete(bot.logout())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
