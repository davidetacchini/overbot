import re
import platform

import distro
import psutil
import discord
from bs4 import BeautifulSoup
from discord.ext import tasks, commands


class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update.start()
        self.statistics.start()
        self.send_overwatch_news.start()

    async def get_statistics(self):
        total_commands = await self.bot.total_commands()
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

        statistics = {
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
                "Uptime": str(self.bot.get_uptime(brief=True)),
                "Ping": f"{self.bot.ping}ms",
                "Lines of Code": self.bot.total_lines,
            },
            "shards": shards,
        }
        return statistics

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
        return all_commands

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
        return servers

    @tasks.loop(seconds=20.0)
    async def statistics(self):
        """POST bot statistics to private API."""
        await self.bot.wait_until_ready()

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.bot.config.obapi["token"],
        }

        payload_statistics = await self.get_statistics()
        payload_commands = await self.get_commands()
        payload_servers = await self.get_servers()

        await self.bot.session.post(
            f'{self.bot.config.obapi["url"]}/statistics',
            json=payload_statistics,
            headers=headers,
        )
        await self.bot.session.post(
            f'{self.bot.config.obapi["url"]}/commands',
            json=payload_commands,
            headers=headers,
        )
        await self.bot.session.post(
            f'{self.bot.config.obapi["url"]}/servers',
            json=payload_servers,
            headers=headers,
        )

    @tasks.loop(minutes=30.0)
    async def update(self):
        """Updates Bot stats on Discord portals."""
        if self.bot.is_beta:
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
        payload = {
            "guildCount": len(self.bot.guilds),
            "shardCount": self.bot.shard_count,
        }

        headers = {
            "Authorization": self.bot.config.discord_bots["token"],
            "Content-Type": "application/json",
        }

        await self.bot.session.post(
            self.bot.config.discord_bots["url"], json=payload, headers=headers
        )

    @tasks.loop(minutes=5.0)
    async def send_overwatch_news(self):
        if self.bot.is_beta:
            return
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
        date = news.find("p", {"class": "Card-date"})

        embed = discord.Embed()
        embed.title = title.get_text()
        embed.url = "https://playoverwatch.com" + news["href"]
        embed.set_author(name="Blizzard Entertainment")
        embed.set_footer(text=date.get_text())
        embed.set_image(url=f"https:{img_url}")

        c = self.bot.get_channel(self.bot.config.news_channel)
        await c.send(embed=embed)

        await self.bot.pool.execute(
            "UPDATE news SET news_id=$1 WHERE id=1;", int(news_id)
        )

    def cog_unload(self):
        self.update.cancel()
        self.statistics.cancel()
        self.send_overwatch_news.cancel()


def setup(bot):
    bot.add_cog(Tasks(bot))
