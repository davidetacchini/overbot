import asyncio
import platform

import distro
import psutil
import aiohttp_cors
from aiohttp import web
from discord.ext import tasks, commands


class Api(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        bot.loop.create_task(self._start())
        bot.loop.create_task(self._format_stats())
        bot.loop.create_task(self._format_servers())

    async def _start(self):
        app = web.Application()
        cors = aiohttp_cors.setup(app)

        app.add_routes(
            [
                web.get(("/stats"), self._get_stats),
                web.get(("/servers"), self._get_servers),
                web.get(("/commands"), self._get_commands),
            ]
        )

        cors = aiohttp_cors.setup(
            app,
            defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=False,
                    expose_headers="*",
                    allow_headers="*",
                )
            },
        )

        for route in list(app.router.routes()):
            cors.add(route)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, port=8000)

        await site.start()

    def _format_commands(self):
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

    async def _format_servers(self):
        if not self.bot.is_ready():
            await asyncio.sleep(15)
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

    async def _format_stats(self):
        if not self.bot.is_ready():
            await asyncio.sleep(15)
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

        return {
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
                "Session Commands": self.bot.commands_used,
                "Uptime": str(self.bot.uptime),
                "Ping": f"{self.bot.ping}ms",
                "Lines of Code": self.bot.total_lines,
            },
            "shards": shards,
        }

    @tasks.loop(minutes=2.0)
    async def _format_stats_loop(self):
        await self._format_stats()
        await self._format_servers()

    async def _get_stats(self, request):
        payload = await self._format_stats()
        return web.json_response(payload)

    async def _get_servers(self, request):
        payload = await self._format_servers()
        return web.json_response(payload)

    def _get_commands(self, request):
        payload = self._format_commands()
        return web.json_response(payload)

    def cog_unload(self):
        self.bot.loop.create_task(self._start().close())
        self._format_stats.cancel()
        self._format_servers.cancel()


def setup(bot):
    bot.add_cog(Api(bot))
