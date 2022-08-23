import os
import sys
import logging

from typing import Any, Sequence

import asyncpg
import discord

from aiohttp import ClientSession
from discord.ext import commands

import config  # type: reportMissingImports=false

from utils import emojis
from classes.ui import PromptView
from utils.time import human_timedelta
from utils.scrape import get_overwatch_maps, get_overwatch_heroes
from classes.paginator import Paginator
from utils.error_handler import error_handler

if sys.platform == "linux":
    import uvloop

    uvloop.install()


log = logging.getLogger("overbot")


class OverBot(commands.AutoShardedBot):
    """Custom bot class for OverBot."""

    pool: asyncpg.Pool
    app_info: discord.AppInfo

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(command_prefix=config.default_prefix, **kwargs)
        self.config = config
        self.sloc: int = 0

        # caching
        self.premiums: set[int] = set()
        self.embed_colors: dict[int, int] = {}
        self.heroes: dict[str, dict[str, str]] = {}
        self.maps: list[dict[str, str | list[str]]] = []

        self.TEST_GUILD: discord.Object = discord.Object(config.test_guild_id)

    @property
    def owner(self) -> discord.User:
        return self.app_info.owner

    @property
    def version(self) -> str:
        return config.version

    @property
    def debug(self) -> bool:
        return config.DEBUG

    @property
    def webhook(self) -> discord.Webhook:
        wh_id, wh_token = config.webhook.values()
        return discord.Webhook.partial(id=wh_id, token=wh_token, session=self.session)

    def color(self, member_id: None | int = None) -> int:
        if member_id is None:
            return config.main_color
        return self.embed_colors.get(member_id, config.main_color)

    def get_uptime(self, *, brief: bool = False) -> str:
        return human_timedelta(self.uptime, accuracy=None, brief=brief, suffix=False)

    async def total_commands(self) -> int:
        total_commands: int = await self.pool.fetchval("SELECT COUNT(*) FROM command;")
        return total_commands + config.old_commands_count

    async def get_pg_version(self) -> str:
        async with self.pool.acquire() as con:
            pg_version = con.get_server_version()

        return f"{pg_version.major}.{pg_version.micro} {pg_version.releaselevel}"

    async def paginate(
        self,
        entries: discord.Embed | str | Sequence[discord.Embed | str],
        *,
        interaction: discord.Interaction,
        **kwargs: Any,
    ) -> None:
        paginator = Paginator(entries, interaction=interaction, **kwargs)
        await paginator.start()

    async def prompt(
        self, interaction: discord.Interaction, payload: str | discord.Embed
    ) -> None | bool:
        kwargs: dict[str, Any]
        if isinstance(payload, str):
            kwargs = {"content": payload}
        elif isinstance(payload, discord.Embed):
            kwargs = {"embed": payload}

        view = PromptView(interaction=interaction)

        if interaction.response.is_done():
            view.message = await interaction.followup.send(**kwargs, view=view)
        else:
            await interaction.response.send_message(**kwargs, view=view)

        await view.wait()
        return view.value

    def tick(self, opt: None | bool) -> discord.PartialEmoji:
        lookup = {
            True: emojis.online,
            False: emojis.dnd,
            None: emojis.offline,
        }
        return lookup.get(opt, emojis.dnd)

    def compute_sloc(self) -> None:
        """Compute source lines of code."""
        for root, dirs, files in os.walk(os.getcwd()):
            dirs[:] = set(dirs) - {"env"}
            for file in files:
                if file.endswith(".py"):
                    with open(f"{root}/{file}") as fp:
                        self.sloc += len(fp.readlines())

    def is_it_premium(self, *to_check) -> bool:
        """Check for a member/guild to be premium."""
        return any(x in self.premiums for x in to_check)

    def get_profiles_limit(self, interaction: discord.Interaction, user_id: int) -> int:
        guild_id = interaction.guild_id or 0
        if not self.is_it_premium(user_id, guild_id):
            return config.DEFAULT_PROFILES_LIMIT
        return config.PREMIUM_PROFILES_LIMIT

    async def _cache_premiums(self) -> None:
        query = """SELECT id
                   FROM member
                   WHERE member.premium = true
                   UNION
                   SELECT id
                   FROM server
                   WHERE server.premium = true;
                """
        ids = await self.pool.fetch(query)
        self.premiums = {i["id"] for i in ids}

    async def _cache_heroes(self) -> None:
        self.heroes = await get_overwatch_heroes()

    async def _cache_maps(self) -> None:
        self.maps = await get_overwatch_maps()

    async def _cache_embed_colors(self) -> None:
        embed_colors = {}
        query = "SELECT id, embed_color FROM member WHERE embed_color IS NOT NULL;"
        colors = await self.pool.fetch(query)
        for member_id, color in colors:
            embed_colors[member_id] = color
        self.embed_colors = embed_colors

    async def setup_hook(self) -> None:
        self.session = ClientSession()
        self.pool = await asyncpg.create_pool(**config.database, max_size=20, command_timeout=60.0)

        self.app_info = await self.application_info()

        self.compute_sloc()

        # caching
        await self._cache_premiums()
        await self._cache_embed_colors()
        await self._cache_heroes()
        await self._cache_maps()

        for extension in os.listdir("cogs"):
            if extension.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{extension[:-3]}")
                except Exception:
                    log.exception(f"Extension {extension} failed its loading.")
                else:
                    log.info(f"Extension {extension} successfully loaded.")

        self.tree.on_error = error_handler

        if self.debug:
            self.tree.copy_global_to(guild=self.TEST_GUILD)
            await self.tree.sync(guild=self.TEST_GUILD)
        else:
            await self.tree.sync()

    async def close(self) -> None:
        await super().close()
        await self.session.close()
        await self.pool.close()


def main() -> None:
    # setup bot logger
    discord.utils.setup_logging()

    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True
    intents.reactions = True
    intents.messages = True

    bot = OverBot(
        activity=discord.Game(name="Starting..."),
        status=discord.Status.dnd,
        allowed_mentions=discord.AllowedMentions.none(),
        application_id=550359245963526194,
        intents=intents,
        chunk_guilds_at_startup=False,
        guild_ready_timeout=5,
    )

    bot.run(config.token, log_handler=None, reconnect=True)


if __name__ == "__main__":
    main()
