import re
import time
import textwrap
from random import randint

import discord
from bs4 import BeautifulSoup
from discord.ext import tasks, commands


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.send_news.start()

    @commands.Cog.listener()
    async def on_ready(self):
        """Print info in the terminal."""
        print(
            textwrap.dedent(
                f"""
            -----------------
            Connection established.
            Logged in as {self.bot.user.display_name} - {self.bot.user.id}
            Using discord.py {discord.__version__}
            Running {self.bot.user.display_name} {self.bot.version} in {len(self.bot.guilds)} guilds
            -----------------
            """
            )
        )
        await self.change_presence()

    @commands.Cog.listener()
    async def on_resumed(self):
        print("Connection resumed.")

    @commands.Cog.listener()
    async def on_connect(self):
        if not self.bot.start_time:
            self.bot.start_time = time.perf_counter()

    async def change_presence(self):
        await self.bot.wait_until_ready()
        await self.bot.change_presence(
            activity=discord.Activity(
                name=f"{self.bot.config.default_prefix}help",
                type=discord.ActivityType.playing,
            ),
            status=discord.Status.idle,
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.bot.pool.execute(
            'INSERT INTO server (id, "prefix") VALUES ($1, $2);',
            guild.id,
            self.bot.config.default_prefix,
        )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        await self.bot.pool.execute("DELETE FROM server WHERE id=$1;", guild.id)

    @tasks.loop(minutes=5.0)
    async def send_news(self):
        await self.bot.wait_until_ready()
        async with self.bot.session.get(self.bot.config.overwatch["news"]) as r:
            content = await r.read()
        page = BeautifulSoup(content, features="html.parser")
        news = page.find("section", {"class": "NewsHeader-featured"}).findChild()
        # get the news ID from the URL
        news_id = re.search(r"\d+", news["href"]).group(0)

        if int(news_id) == await self.bot.pool.fetchval(
            "SELECT news_id FROM news WHERE id=1;"
        ):
            return

        title = news.find("h1", {"class": "Card-title"})
        img = news.find("div", {"class", "Card-thumbnail"})
        img_url = img["style"].split("url(")[1][:-1]

        embed = discord.Embed(
            title=title.get_text(),
            url="https://playoverwatch.com" + news["href"],
            color=self.bot.color,
            timestamp=self.bot.timestamp,
        )

        embed.set_image(url=f"https:{img_url}")
        embed.set_footer(text="Blizzard Entertainment")
        if randint(0, 2) == 1:
            embed.add_field(
                name="Info",
                value="You can disable news feed notification by running the `settings news disable`.",
            )

        channels = await self.bot.pool.fetch(
            "SELECT news_channel FROM server WHERE news_channel <> 0;"
        )

        for channel in channels:
            c = self.bot.get_channel(channel["news_channel"])
            try:
                await c.send(embed=embed)
            except AttributeError:
                # if the channel set for the news notification has been deleted, reset to 0
                await self.bot.pool.execute(
                    "UPDATE server SET news_channel=0 WHERE news_channel=$1;",
                    channel["news_channel"],
                )

        await self.bot.pool.execute(
            "UPDATE news SET news_id=$1 WHERE id=1;", int(news_id)
        )

    def cog_unload(self):
        self.send_news.cancel()


def setup(bot):
    bot.add_cog(Events(bot))
