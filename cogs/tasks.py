from __future__ import annotations

import re
import platform

from typing import TYPE_CHECKING

import distro
import psutil
import discord

from discord.ext import tasks, commands

from utils.scrape import get_overwatch_news

if TYPE_CHECKING:
    from bot import OverBot


class Tasks(commands.Cog):
    def __init__(self, bot: OverBot):
        self.bot = bot

    async def setup_hook(self) -> None:
        self.update_discord_portals.start()
        self.update_private_api.start()
        self.check_subscriptions.start()
        self.send_overwatch_news.start()

    def get_shards(self) -> list[dict]:
        shards = []
        for shard in self.bot.shards.values():
            guilds = [g for g in self.bot.guilds if g.shard_id == shard.id]
            try:
                total_members = sum(g.member_count for g in guilds)
            except AttributeError:
                total_members = 0
            shards.append(
                {
                    "id": shard.id + 1,
                    "latency": round(shard.latency * 1000, 2),
                    "guild_count": len(guilds),
                    "member_count": total_members,
                }
            )
        return shards

    async def get_bot_stats(self) -> dict[str, dict]:
        total_commands = await self.bot.total_commands()

        try:
            total_members = sum(g.member_count for g in self.bot.guilds)
        except AttributeError:
            total_members = 0

        large_servers = sum(1 for g in self.bot.guilds if g.large)

        try:
            shards = self.get_shards()
            ping = f"{round(self.bot.latency * 1000, 2)}ms"
        except OverflowError:
            shards = []
            ping = "N/A"

        pg_version = await self.bot.get_pg_version()

        os_name = distro.linux_distribution()[0]
        os_version = distro.linux_distribution()[1]

        return {
            "host": {
                "Postgres": pg_version,
                "Python": platform.python_version(),
                "OS": os_name + " " + os_version,
                "CPU Percent": f"{psutil.cpu_percent()}%",
                "CPU Cores": psutil.cpu_count(),
                "CPU Frequency": f"{round(psutil.cpu_freq()[0] / 1000, 2)}GHz",
                "RAM Usage": f"{psutil.virtual_memory()[2]}%",
            },
            "bot": {
                "Servers": len(self.bot.guilds),
                "Shards": self.bot.shard_count,
                "Members": total_members,
                "Large servers": large_servers,
                "Commands runned": total_commands,
                "Uptime": str(self.bot.get_uptime(brief=True)),
                "Websocket latency": ping,
                "Lines of code": self.bot.sloc,
            },
            "shards": shards,
        }

    async def get_bot_commands(self) -> list[dict]:
        all_commands = []
        for command in self.bot.walk_commands():
            if command.hidden:
                continue
            all_commands.append(
                {
                    "cog": command.cog_name,
                    "name": command.qualified_name,
                    "aliases": command.aliases or None,
                    "cooldown": command.cooldown.per if command.cooldown else None,
                    "signature": command.signature or None,
                    "is_premium": command.extras.get("premium") or False,
                    "short_desc": command.short_doc or "No help found...",
                    "long_desc": command.help or "No help found...",
                }
            )
        return all_commands

    async def get_top_servers(self) -> list[dict]:
        guilds = await self.bot.get_cog("Meta").get_weekly_top_guilds(self.bot)
        servers = []
        for guild in guilds:
            g = self.bot.get_guild(guild["guild_id"])
            if g is None:
                continue
            icon = str(g.icon.replace(size=128, format="webp")) if g.icon else ""
            servers.append(
                {
                    "id": g.id,
                    "name": str(g),
                    "icon": icon,
                    "members": g.member_count,
                    "commands_run": guild["commands"],
                    "shard_id": g.shard_id + 1,
                    "joined_at": str(g.me.joined_at),
                    "is_premium": g.id in self.bot.premiums,
                }
            )
        return servers

    @tasks.loop(seconds=30.0)
    async def update_private_api(self) -> None:
        """POST bot stats to private API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": self.bot.config.obapi["token"],
        }

        stats = await self.get_bot_stats()
        commands = await self.get_bot_commands()
        servers = await self.get_top_servers()

        BASE_URL = self.bot.config.obapi["url"]
        await self.bot.session.post(f"{BASE_URL}/statistics", json=stats, headers=headers)
        await self.bot.session.post(f"{BASE_URL}/commands", json=commands, headers=headers)
        await self.bot.session.post(f"{BASE_URL}/servers", json=servers, headers=headers)

    @update_private_api.before_loop
    async def before_update_private_api(self):
        if self.bot.debug:
            return

        await self.bot.wait_until_ready()

    @tasks.loop(minutes=30.0)
    async def update_discord_portals(self):
        """Updates bot stats on Discord portals."""
        # POST stats on top.gg
        payload = {
            "server_count": len(self.bot.guilds),
            "shard_count": self.bot.shard_count,
        }

        top_gg_headers = {"Authorization": self.bot.config.top_gg["token"]}

        await self.bot.session.post(
            self.bot.config.top_gg["url"], data=payload, headers=top_gg_headers
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

    @update_discord_portals.before_loop
    async def before_update_discord_portals(self):
        if self.bot.debug:
            return

        await self.bot.wait_until_ready()

    async def set_premium_for(self, target_id: int, *, server: bool = True) -> None:
        server_query = """INSERT INTO server (id)
                          VALUES ($1)
                          ON CONFLICT (id) DO
                          UPDATE SET premium = true;
                       """
        member_query = """INSERT INTO member (id)
                          VALUES ($1)
                          ON CONFLICT (id) DO
                          UPDATE SET premium = true;
                       """
        if server:
            await self.bot.pool.execute(server_query, target_id)
        else:
            await self.bot.pool.execute(member_query, target_id)

    @tasks.loop(minutes=5.0)
    async def check_subscriptions(self):
        url_new = self.bot.config.dbot["new"]  # endpoint to check for new donations
        product_server_id = self.bot.config.dbot["product_ids"]["server"]

        headers = {"Authorization": self.bot.config.dbot["api_key"]}

        async with self.bot.session.get(url_new, headers=headers) as r:
            subscriptions = await r.json()

        try:
            donations = subscriptions["donations"]
        except KeyError:
            return

        if not donations:
            return

        for donation in donations:
            if donation["product_id"] == product_server_id:
                guild_id = int(donation["seller_customs"]["Server ID (to be set as premium)"])
                await self.set_premium_for(guild_id)
                self.bot.premiums.add(guild_id)
            else:
                member_id = int(donation["buyer_id"])
                await self.set_premium_for(member_id, server=False)
                self.bot.premiums.add(member_id)

            # endpoint to mark donation as processed
            url_mark = self.bot.config.dbot["mark"].format(donation["txn_id"])
            payload = {"markProcessed": True}
            async with self.bot.session.post(url_mark, json=payload, headers=headers) as r:
                message = f'Donation {donation["txn_id"]} has been processed. Status {r.status}'
                await self.bot.get_cog("Events").send_log(message, discord.Color.blurple())

    @check_subscriptions.before_loop
    async def before_check_subscriptions(self):
        if self.bot.debug:
            return

        await self.bot.wait_until_ready()

    @tasks.loop(minutes=5.0)
    async def send_overwatch_news(self):
        try:
            news = (await get_overwatch_news(1))[0]
        except AttributeError:
            return

        # get the news id from the URL
        latest_news_id = re.search(r"\d+", news["link"]).group(0)

        # check whether the scraped news id is equals to the
        # one stored in the file; if not then there's a news
        file = open("assets/latest_news_id.txt", "r+")
        file_news_id = file.readline()
        if int(latest_news_id) == int(file_news_id):
            file.close()
            return

        embed = discord.Embed()
        embed.title = news["title"]
        embed.url = news["link"]
        embed.set_author(name="Blizzard Entertainment")
        embed.set_image(url=f'https:{news["thumbnail"]}')
        embed.set_footer(text=news["date"])

        records = await self.bot.pool.fetch("SELECT id FROM newsboard;")
        for record in records:
            channel_id = record["id"]
            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue
            await channel.send(embed=embed)

        # update old news_id with latest one
        file.seek(0)
        file.write(latest_news_id)
        file.truncate()
        file.close()

    @send_overwatch_news.before_loop
    async def before_send_overwatch_news(self):
        if self.bot.debug:
            return

        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.update_discord_portals.cancel()
        self.update_private_api.cancel()
        self.check_subscriptions.cancel()
        self.send_overwatch_news.cancel()


async def setup(bot: OverBot):
    await bot.add_cog(Tasks(bot))
