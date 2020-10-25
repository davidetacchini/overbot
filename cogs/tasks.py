import re
import json
import platform
from random import randint

import distro
import psutil
import discord
from bs4 import BeautifulSoup
from discord.ext import tasks, commands

from utils.player import Player


class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update.start()
        self.statistics.start()
        self.send_news.start()
        self.track_profile.start()

    async def get_statistics(self):
        total_commands = await self.bot.pool.fetchval("SELECT SUM(used) FROM command;")
        total_members = sum(guild.member_count for guild in self.bot.guilds)
        large_servers = sum(1 for guild in self.bot.guilds if guild.large)
        latencies = dict(s for s in self.bot.latencies)
        shards = dict((k + 1, round(v * 1000)) for k, v in latencies.items())
        async with self.bot.pool.acquire() as conn:
            pg_version = conn.get_server_version()
        pg_version = f"{pg_version.major}.{pg_version.micro} {pg_version.releaselevel}"
        py_version = platform.python_version()
        os_name = distro.linux_distribution()[0]
        os_version = distro.linux_distribution()[1]
        cpu_perc = f"{psutil.cpu_percent()}%"
        cpu_cores = psutil.cpu_count()
        cpu_freq = f"{round(psutil.cpu_freq()[0] / 1000, 2)}GHz"
        ram = f"{psutil.virtual_memory()[2]}%"

        statistics = json.dumps(
            {
                "host": {
                    "Postgres Version": pg_version,
                    "Python Version": py_version,
                    "O.S. Name": os_name,
                    "O.S. Version": os_version,
                    "CPU Percent": cpu_perc,
                    "CPU Cores": cpu_cores,
                    "CPU Frequency": cpu_freq,
                    "RAM Usage": ram,
                },
                "bot": {
                    "Servers": len(self.bot.guilds),
                    "Shards": self.bot.shard_count,
                    "Members": total_members,
                    "Large Servers": large_servers,
                    "Total Commands": total_commands,
                    "Uptime": str(self.bot.uptime),
                    "Ping": f"{self.bot.ping}ms",
                    "Lines of Code": self.bot.total_lines,
                },
                "shards": shards,
            }
        )
        return json.dumps(statistics)

    async def get_commands(self):
        all_commands = []
        for command in self.bot.walk_commands():
            current_command = self.bot.get_command(command.qualified_name)
            if current_command.cog_name == "Owner":
                continue
            all_commands.append(
                dict(
                    cog=current_command.cog_name,
                    name=current_command.qualified_name,
                    aliases=current_command.aliases or None,
                    signature=current_command.signature or None,
                    description=getattr(current_command.callback, "__doc__"),
                    brief=current_command.brief,
                )
            )
        return json.dumps(all_commands)

    async def get_servers(self):
        guilds = await self.bot.pool.fetch(
            "SELECT id, commands_runned FROM server ORDER BY commands_runned DESC LIMIT 5;"
        )
        servers = []
        for guild in guilds:
            g = self.bot.get_guild(guild["id"])
            servers.append(
                dict(
                    id=g.id,
                    name=str(g),
                    icon=str(g.icon_url),
                    commands_runned=guild["commands_runned"],
                )
            )
        return json.dumps(servers)

    @tasks.loop(minutes=30.0)
    async def update(self):
        """Updates Bot stats on Discord portals."""
        if self.bot.config.is_beta:
            return

        # POST stats on top.gg
        payload = {
            "server_count": len(self.bot.guilds),
            "shard_count": self.bot.shard_count,
        }

        topgg_headers = {"Authorization": self.bot.config.top_gg["token"]}

        await self.bot.session.post(
            self.bot.config.top_gg["url"], data=payload, headers=topgg_headers
        )

        # POST stats on discordbotlist.com
        dbl_payload = {"guilds": len(self.bot.guilds), "users": len(self.bot.users)}

        dbl_headers = {"Authorization": f'Bot {self.bot.config.dbl["token"]}'}

        await self.bot.session.post(
            self.bot.config.dbl["url"], data=dbl_payload, headers=dbl_headers
        )

        # POST stats on discord.bots.gg
        payload = json.dumps(
            {
                "guildCount": len(self.bot.guilds),
                "shardCount": self.bot.shard_count,
            }
        )

        headers = {
            "Authorization": self.bot.config.discord_bots["token"],
            "Content-Type": "application/json",
        }

        await self.bot.session.post(
            self.bot.config.discord_bots["url"], data=payload, headers=headers
        )

    @tasks.loop(seconds=30.0)
    async def statistics(self):
        """POST bot statistics to private API."""
        if self.bot.config.is_beta:
            return
        await self.bot.wait_until_ready()

        payload_statistics = await self.get_statistics()
        payload_commands = await self.get_commands()
        payload_servers = await self.get_servers()

        headers = {
            "Content-Type": "application/json",
        }

        await self.bot.session.post(
            f"{self.bot.config.obapi}/statistics",
            data=payload_statistics,
            headers=headers,
        )

        await self.bot.session.post(
            f"{self.bot.config.obapi}/commands", data=payload_commands, headers=headers
        )

        await self.bot.session.post(
            f"{self.bot.config.obapi}/servers", data=payload_servers, headers=headers
        )

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

    @tasks.loop(hours=24.0)
    async def track_profile(self):
        await self.bot.wait_until_ready()
        if self.bot.is_ready():
            # don't send the message everytime the bot starts
            return

        profiles = await self.bot.pool.fetch(
            "SELECT id, platform, name FROM profile WHERE track <> false"
        )
        for profile in profiles:
            user = self.bot.get_user(profile["id"])
            data = await self.bot.data.Data(
                platform=profile["platform"], name=profile["name"]
            ).get()

            try:
                await user.send(
                    embed=Player(
                        data=data, platform=profile["platform"], name=profile["name"]
                    ).rank()
                )
            except discord.Forbidden:
                return

    def cog_unload(self):
        self.update.cancel()
        self.statistics.cancel()
        self.send_news.cancel()
        self.track_profile.cancel()


def setup(bot):
    bot.add_cog(Tasks(bot))
