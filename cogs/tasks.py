from __future__ import annotations

import logging
import platform
import re
from typing import TYPE_CHECKING, Any

import discord
import distro
import psutil
from discord.app_commands import Group as AppCommandsGroup
from discord.ext import commands, tasks

from utils.scrape import get_overwatch_news

if TYPE_CHECKING:
    from bot import OverBot

    Shards = BotCommands = TopServers = Supporters = list[dict[str, Any]]
    BotStats = dict[str, list[dict[str, Any]] | dict[str, Any]]


log = logging.getLogger(__name__)


class Tasks(commands.Cog):
    def __init__(self, bot: OverBot) -> None:
        self.bot = bot
        self.update_private_api.start()
        self.send_overwatch_news.start()
        self.update_bot_presence.start()

    def get_shards(self) -> Shards:
        shards = []
        for shard in self.bot.shards.values():
            guilds = [g for g in self.bot.guilds if g.shard_id == shard.id]
            try:
                total_members = sum(g.member_count for g in guilds if g.member_count)
            except (AttributeError, TypeError):
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

    async def get_bot_stats(self) -> BotStats:
        total_commands = await self.bot.total_commands()

        try:
            total_members = sum(g.member_count for g in self.bot.guilds if g.member_count)
        except (AttributeError, TypeError):
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

        # it seems psutil is unable to read cpu_freq when running docker on top of M1 chip.
        try:
            cpu_frequency = f"{round(psutil.cpu_freq()[0] / 1000, 2)}GHz"
        except TypeError:
            cpu_frequency = "N/A"

        cpu_percent = f"{psutil.cpu_percent()}%"
        cpu_cores = psutil.cpu_count()
        ram_usage = f"{psutil.virtual_memory()[2]}%"

        return {
            "host": {
                "Postgres": pg_version,
                "Python": platform.python_version(),
                "OS": os_name + " " + os_version,
                "CPU Percent": cpu_percent,
                "CPU Cores": cpu_cores,
                "CPU Frequency": cpu_frequency,
                "RAM Usage": ram_usage,
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
                "Version": self.bot.version,
            },
            "shards": shards,
        }

    def get_bot_commands(self) -> BotCommands:
        all_commands = []

        def get_command_type(command):
            # App Commands does not have 'type' attribute
            try:
                command.type
            except AttributeError:
                return "App Command"
            else:
                return "Context Menu"

        context_menus = self.bot.tree.get_commands(type=discord.AppCommandType.user)
        for command in context_menus:
            all_commands.append(
                {
                    "cog": getattr(command, "__cog_name__"),
                    "name": command.qualified_name,
                    "type": get_command_type(command),
                    "is_premium": command.extras.get("premium", False),
                    "description": command.callback.__doc__,
                    "guild_only": False,
                }
            )

        for cog_name, cog in self.bot.cogs.items():
            if cog_name.lower() == "owner":
                continue
            for command in cog.walk_app_commands():
                if isinstance(command, AppCommandsGroup):
                    continue  # groups are not commands
                all_commands.append(
                    {
                        "cog": cog_name,
                        "name": command.qualified_name,
                        "type": get_command_type(command),
                        "is_premium": command.extras.get("premium", False),
                        "description": command.description or "No description found...",
                        "guild_only": command.guild_only,
                    }
                )

        return all_commands

    async def get_top_servers(self) -> TopServers:
        guilds = await self.bot.get_cog("Meta").get_weekly_top_guilds(self.bot)  # type: ignore
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
                    "joined_at": str(g.me.joined_at) if g.me is not None else "N/A",
                    "is_premium": g.id in self.bot.premiums,
                }
            )
        return servers

    async def get_supporters(self) -> Supporters:
        supporters = []
        for id_ in self.bot.premiums:
            if id_ == self.bot.config.owner_id:  # skip my profile
                continue
            guild = self.bot.get_guild(id_)
            if guild is not None:
                icon = str(guild.icon.replace(size=128, format="webp")) if guild.icon else ""
                supporters.append(
                    {
                        "id": id_,
                        "name": str(guild),
                        "icon": icon,
                        "is_server": True,
                    }
                )
            else:
                try:
                    user = self.bot.get_user(id_) or (await self.bot.fetch_user(id_))
                except Exception:
                    pass
                else:
                    icon = str(user.display_avatar.replace(size=128, format="webp"))
                    supporters.append(
                        {
                            "id": id_,
                            "name": str(user),
                            "icon": icon,
                            "is_server": False,
                        }
                    )
        return supporters

    @tasks.loop(seconds=30.0)
    async def update_private_api(self):
        """POST bot stats to private API."""
        await self.bot.wait_until_ready()

        headers = {
            "Content-Type": "application/json",
            "Authorization": self.bot.config.obapi["token"],
        }

        stats = await self.get_bot_stats()
        commands = self.get_bot_commands()
        servers = await self.get_top_servers()
        supporters = await self.get_supporters()

        if self.bot.debug:
            try:
                BASE_URL = self.bot.config.obapi["dev"]
            except KeyError:
                return
        else:
            BASE_URL = self.bot.config.obapi["prod"]

        await self.bot.session.post(f"{BASE_URL}/statistics", json=stats, headers=headers)
        await self.bot.session.post(f"{BASE_URL}/commands", json=commands, headers=headers)
        await self.bot.session.post(f"{BASE_URL}/servers", json=servers, headers=headers)
        await self.bot.session.post(f"{BASE_URL}/supporters", json=supporters, headers=headers)

    @tasks.loop(minutes=5.0)
    async def send_overwatch_news(self):
        if self.bot.debug:
            return

        await self.bot.wait_until_ready()

        try:
            news = (await get_overwatch_news(session=self.bot.session))[0]
        except Exception:
            return

        # get the news id from the URL
        latest_news_id = re.search(r"\d+", news["link"]).group(0)  # type: ignore

        # check whether the scraped news id is equals to the
        # one stored in the file; if not then there's a news
        db_news_id = await self.bot.pool.fetchval("SELECT latest_id FROM news WHERE id = 1;")

        if int(latest_news_id) == int(db_news_id):
            return

        embed = discord.Embed()
        embed.title = news["title"]
        embed.url = news["link"]
        embed.set_author(name="Blizzard Entertainment")
        embed.set_image(url=news["thumbnail"])
        embed.set_footer(text=news["date"])

        records = await self.bot.pool.fetch("SELECT id FROM newsboard;")
        for record in records:
            channel_id = record["id"]
            channel = self.bot.get_channel(channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                continue
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                continue

        # update old news_id with latest one
        await self.bot.pool.execute(
            "UPDATE news SET latest_id = $1 WHERE id = 1", int(latest_news_id)
        )
        log.info("News ID has been successfully updated.")

    @tasks.loop(hours=1.0)
    async def update_bot_presence(self):
        await self.bot.wait_until_ready()
        game = discord.Game("/help")
        await self.bot.change_presence(activity=game)

    def cog_unload(self) -> None:
        self.update_private_api.cancel()
        self.send_overwatch_news.cancel()
        self.update_bot_presence.cancel()


async def setup(bot: OverBot) -> None:
    await bot.add_cog(Tasks(bot))
