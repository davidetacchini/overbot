import os
import re
import asyncio
import datetime
from contextlib import suppress

import asyncpg
import discord
import pygicord
from aiohttp import ClientSession
from termcolor import colored
from discord.ext import commands

import config
from utils import i18n
from utils.time import human_timedelta
from utils.checks import global_cooldown
from utils.scrape import get_overwatch_maps, get_overwatch_heroes
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
        self.config = config
        self.paginator = pygicord
        self.total_lines = 0

        # caching
        self.prefixes = {}
        self.premiums = {}
        self.embed_colors = {}
        self.heroes = []
        self.maps = []
        self.hero_names = []

        self.normal_cooldown = commands.CooldownMapping.from_cooldown(
            1, 3, commands.BucketType.member
        )
        self.premium_cooldown = commands.CooldownMapping.from_cooldown(
            1, 1.5, commands.BucketType.member
        )

        self.add_check(global_cooldown, call_once=True)

    @property
    def timestamp(self):
        return datetime.datetime.utcnow()

    @property
    def prefix(self):
        return config.default_prefix

    @property
    def version(self):
        return config.version

    @property
    def debug(self):
        return config.DEBUG

    @property
    def webhook(self):
        wh_id, wh_token = (config.webhook["id"], config.webhook["token"])
        return discord.Webhook.partial(
            id=wh_id,
            token=wh_token,
            adapter=discord.AsyncWebhookAdapter(self.bot.session),
        )

    def color(self, member_id: int = None):
        return self.embed_colors.get(member_id, config.main_color)

    def get_uptime(self, *, brief=False):
        return human_timedelta(self.uptime, accuracy=None, brief=brief, suffix=False)

    async def total_commands(self):
        total_commands = await self.pool.fetchval("SELECT COUNT(*) FROM command;")
        return total_commands + config.old_commands_count

    async def on_message(self, message):
        if not self.is_ready():
            return
        if message.author.bot:
            return
        await self.process_commands(message)

    async def invoke(self, ctx):
        member_id = ctx.message.author.id
        locale = await self.get_cog("Locale").update_locale(member_id)
        i18n.current_locale.set(locale)
        await super().invoke(ctx)

    async def _get_prefix(self, bot, message):
        if not message.guild:
            return self.prefix
        try:
            return commands.when_mentioned_or(self.prefixes[message.guild.id])(
                self, message
            )
        except KeyError:
            return commands.when_mentioned_or(self.prefix)(self, message)

    async def get_or_fetch_member(self, member_id):
        guild = self.get_guild(config.support_server_id)

        member = guild.get_member(member_id)
        if member is not None:
            return member

        shard = self.get_shard(guild.shard_id)
        if shard.is_ws_ratelimited():
            try:
                member = await guild.fetch_member(member_id)
            except discord.HTTPException:
                return None
            else:
                return member

        members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
        if not members:
            return None
        return members[0]

    def clean_prefix(self, ctx):
        user = ctx.guild.me if ctx.guild else ctx.bot.user
        pattern = re.compile(r"<@!?%s>" % user.id)
        return pattern.sub("@%s" % user.display_name.replace("\\", r"\\"), ctx.prefix)

    async def cleanup(self, message):
        with suppress(discord.HTTPException, discord.Forbidden):
            await message.delete()

    def get_line_count(self):
        for root, dirs, files in os.walk(os.getcwd()):
            [dirs.remove(d) for d in list(dirs) if d == "env"]
            for name in files:
                if name.endswith(".py"):
                    with open(f"{root}/{name}") as f:
                        self.total_lines += len(f.readlines())

    def member_is_premium(self, member_id, guild_id):
        """Check for a member/guild to be premium."""
        to_check = (member_id, guild_id)

        if all(x not in self.premiums for x in to_check):
            return False
        return True

    def get_max_profiles_limit(self, ctx):
        member_id = ctx.author.id
        guild_id = ctx.guild.id if ctx.guild is not None else 0
        if self.member_is_premium(member_id, guild_id):
            return 25
        else:
            return 5

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=Context)

    async def cache_prefixes(self):
        rows = await self.pool.fetch("SELECT id, prefix FROM server;")
        for row in rows:
            if row["prefix"] != self.prefix:
                self.prefixes[row["id"]] = row["prefix"]
        self.command_prefix = self._get_prefix

    async def cache_premiums(self):
        query = """SELECT id
                   FROM member
                   WHERE member.premium = true
                   UNION
                   SELECT id
                   FROM server
                   WHERE server.premium = true;
                """
        ids = await self.pool.fetch(query)
        # make a set of integers
        self.premiums = {i["id"] for i in ids}

    async def cache_heroes(self):
        self.heroes = await get_overwatch_heroes()

    async def cache_maps(self):
        self.maps = await get_overwatch_maps()

    async def cache_hero_names(self):
        self.hero_names = [str(h["key"]).lower() for h in self.heroes]

    async def cache_embed_colors(self):
        embed_colors = {}
        query = "SELECT id, embed_color FROM member WHERE embed_color IS NOT NULL;"
        colors = await self.pool.fetch(query)
        for member_id, color in colors:
            embed_colors[member_id] = color
        self.embed_colors = embed_colors

    async def start(self, *args, **kwargs):
        self.session = ClientSession(loop=self.loop)
        self.pool = await asyncpg.create_pool(
            **config.database, max_size=20, command_timeout=60.0
        )

        self.get_line_count()
        # caching
        await self.cache_prefixes()
        await self.cache_premiums()
        await self.cache_embed_colors()
        await self.cache_heroes()
        await self.cache_hero_names()
        await self.cache_maps()

        for extension in os.listdir("cogs"):
            if extension.endswith(".py"):
                try:
                    self.load_extension(f"cogs.{extension[:-3]}")
                except Exception as e:
                    print(
                        f"[{colored('ERROR', 'red')}] {extension:20} failed its loading!\n[{e}]"
                    )
                else:
                    print(
                        f"[{colored('OK', 'green')}] {extension:20} successfully loaded"
                    )
        await super().start(config.token, reconnect=True)

    async def close(self):
        await self.session.close()
        await self.pool.close()
        await super().close()


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
        loop.run_until_complete(bot.close())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
