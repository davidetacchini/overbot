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
import time
import asyncio
import datetime

import asyncpg
import discord
import pygicord
from bs4 import BeautifulSoup
from aiohttp import ClientSession
from termcolor import colored
from discord.ext import commands

import config
from utils import data
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
        super().__init__(command_prefix=self.get_pre, **kwargs)
        self.remove_command("help")
        self.config = config
        self.start_time = None
        self.total_lines = 0
        self.get_line_count()

        self.paginator = pygicord
        self.data = data

    def __repr__(self):
        return "<Bot>"

    @property
    def uptime(self):
        raw = int(round(time.perf_counter() - self.start_time))
        return datetime.timedelta(seconds=raw)

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

    async def get_pre(self, bot, message):
        if not message.guild:
            return config.default_prefix
        prefix = await self.pool.fetchval(
            "SELECT prefix FROM server WHERE id=$1;", message.guild.id
        )
        if prefix != config.default_prefix:
            return commands.when_mentioned_or(prefix)(bot, message)
        return commands.when_mentioned_or(config.default_prefix)(bot, message)

    def get_subcommands(self, ctx, command):
        subcommands = getattr(command, "commands")
        embed = discord.Embed(color=self.color)
        embed.title = f"{str(command).capitalize()} Commands"
        embed.description = f"Use `{ctx.prefix}help {str(command)} [command]` for more information on a command"
        embed.set_footer(
            text="Replace [command] with one of the commands listed above."
        )
        sub = [f"`{subcommand.name}`" for subcommand in subcommands]
        value = ", ".join(sub)
        embed.add_field(name="Commands Available", value=value)
        embed.add_field(
            name="Usage",
            value=f"`{ctx.prefix}{str(command)} [command]`",
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
        embed.add_field(name="Error", value=exc)
        return embed

    async def get_overbot_status(self):
        async with self.session.get("https://overbot.statuspage.io/") as r:
            content = await r.read()
        page = BeautifulSoup(content, features="html.parser")
        names = [n.get_text() for n in page.find_all("span", {"class": "name"})]
        status = [
            s.get_text() for s in page.find_all("span", {"class": "component-status"})
        ]
        return names, status

    async def get_overwatch_status(self):
        async with self.session.get(self.config.overwatch["status"]) as r:
            content = await r.read()
        page = BeautifulSoup(content, features="html.parser")
        return page.find(class_="entry-title").get_text()

    async def get_overwatch_news(self):
        async with self.session.get(self.config.overwatch["news"]) as r:
            content = await r.read()
        page = BeautifulSoup(content, features="html.parser")
        news = page.find("section", {"class", "NewsHeader-featured"})
        titles = [x.get_text() for x in news.find_all("h1", {"class": "Card-title"})]
        links = ["https://playoverwatch.com" + x["href"] for x in news]
        imgs = [
            x["style"].split("url(")[1][:-1]
            for x in news.find_all("div", {"class", "Card-thumbnail"})
        ]
        dates = [x.get_text() for x in news.find_all("p", {"class": "Card-date"})]
        return titles, links, imgs, dates

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=Context)

    async def start(self, *args, **kwargs):
        self.session = ClientSession(loop=self.loop)
        self.pool = await asyncpg.create_pool(
            **self.config.database, max_size=20, command_timeout=60.0
        )
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
