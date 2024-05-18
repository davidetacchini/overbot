import logging
import os
from typing import Any, Sequence

import discord
from aiohttp import ClientSession
from asyncpg import Pool
from discord.ext import commands

import config
from classes.command_tree import OverBotCommandTree
from classes.paginator import Paginator
from classes.ui import PromptView
from utils import emojis
from utils.time import human_timedelta

log = logging.getLogger(__name__)

__version__ = "6.2.2"


class OverBot(commands.AutoShardedBot):
    """Custom bot class for OverBot."""

    user: discord.ClientUser
    pool: Pool
    app_info: discord.AppInfo

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            command_prefix=config.default_prefix, tree_cls=OverBotCommandTree, **kwargs
        )
        self.config = config
        self.sloc: int = 0

        # caching
        self.premiums: set[int] = set()
        self.embed_colors: dict[int, int] = {}
        self.heroes: dict[str, dict[Any, Any]] = {}
        self.maps: dict[str, dict[Any, Any]] = {}
        self.gamemodes: dict[str, dict[Any, Any]] = {}

        self.BASE_URL: str = config.base_url
        self.TEST_GUILD: discord.Object = discord.Object(config.test_guild_id)

    @property
    def owner(self) -> discord.User:
        return self.app_info.team.owner  # type: ignore # team is not None

    @property
    def version(self) -> str:
        return __version__

    @property
    def debug(self) -> bool:
        return config.debug

    @property
    def webhook(self) -> discord.Webhook:
        wh_id, wh_token = config.webhook.values()
        return discord.Webhook.partial(id=wh_id, token=wh_token, session=self.session)

    def color(self, member_id: None | int = None) -> int:
        if member_id is None:
            return config.main_color
        return self.embed_colors.get(member_id, config.main_color)

    def get_uptime(self, *, brief: bool = False) -> str:
        return human_timedelta(getattr(self, "uptime"), accuracy=None, brief=brief, suffix=False)

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
        if isinstance(payload, str):
            kwargs = {"content": payload, "embed": None}
        elif isinstance(payload, discord.Embed):
            kwargs = {"content": None, "embed": payload}

        view = PromptView(interaction=interaction)

        if interaction.response.is_done():
            view.message = await interaction.followup.send(**kwargs, view=view)
        else:
            await interaction.response.send_message(**kwargs, view=view)

        await view.wait()
        return view.value

    async def insert_member(self, member_id: int) -> None:
        query = """INSERT INTO member (id)
                   VALUES ($1)
                   ON CONFLICT (id) DO NOTHING;
                """
        await self.pool.execute(query, member_id)

    def tick(self, opt: None | bool) -> discord.PartialEmoji:
        lookup = {
            True: emojis.online,
            False: emojis.dnd,
            None: emojis.offline,
        }
        return lookup.get(opt, emojis.dnd)

    def compute_sloc(self) -> None:
        """Compute source lines of code."""

        def read_file_lines(root, file):
            if file.endswith(".py"):
                with open(f"{root}/{file}", "r") as fp:
                    nc = [_.strip() for _ in fp if not _.startswith("#")]  # remove comment lines
                    self.sloc += len([_ for _ in nc if _])  # remove blank lines

        for root, dirs, files in os.walk(os.getcwd()):
            dirs[:] = set(dirs) - {"env"}
            for file in files:
                read_file_lines(root, file)

    def is_it_premium(self, *to_check) -> bool:
        """Check for a member/guild to be premium."""
        return any(x in self.premiums for x in to_check)

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

    async def _cache_embed_colors(self) -> None:
        embed_colors = {}
        query = "SELECT id, embed_color FROM member WHERE embed_color IS NOT NULL;"
        colors = await self.pool.fetch(query)
        for member_id, color in colors:
            embed_colors[member_id] = color
        self.embed_colors = embed_colors

    async def _cache_heroes(self) -> None:
        try:
            data = await self.session.get(f"{self.BASE_URL}/heroes")
        except Exception:
            log.exception("Cannot get heroes. Aborting...")
            await self.close()
        else:
            data = await data.json()
            heroes = {}
            for hero in data:
                heroes[hero.pop("key")] = hero
            self.heroes = heroes
            log.info("Heroes successfully cached.")

    async def _cache_maps(self) -> None:
        try:
            data = await self.session.get(f"{self.BASE_URL}/maps")
        except Exception:
            log.exception("Cannot get maps. Aborting...")
            await self.close()
        else:
            data = await data.json()
            maps = {}
            for map_ in data:
                maps[map_.get("name")] = map_
            self.maps = maps
            log.info("Maps successfully cached.")

    async def _cache_gamemodes(self) -> None:
        try:
            data = await self.session.get(f"{self.BASE_URL}/gamemodes")
        except Exception:
            log.exception("Cannot get gamemodes. Aborting...")
            await self.close()
        else:
            data = await data.json()
            gamemodes = {}
            for gamemode in data:
                gamemodes[gamemode.pop("key")] = gamemode
            self.gamemodes = gamemodes
            log.info("Gamemodes successfully cached.")

    async def setup_hook(self) -> None:
        self.session = ClientSession()

        self.app_info = await self.application_info()

        self.compute_sloc()

        # caching
        await self._cache_premiums()
        await self._cache_embed_colors()
        await self._cache_heroes()
        await self._cache_maps()
        await self._cache_gamemodes()

        for extension in os.listdir("cogs"):
            if extension.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{extension[:-3]}")
                except Exception:
                    log.exception(f"Extension {extension} failed its loading.")
                else:
                    log.info(f"Extension {extension} successfully loaded.")

        if self.debug:
            self.tree.copy_global_to(guild=self.TEST_GUILD)
            await self.tree.sync(guild=self.TEST_GUILD)
        else:
            await self.tree.sync()
            await self.tree.sync(guild=self.TEST_GUILD)

    async def start(self) -> None:
        await super().start(config.token, reconnect=True)

    async def close(self) -> None:
        await super().close()
        await self.session.close()
        await self.pool.close()

        for handler in log.handlers[:]:
            handler.close()
            log.removeHandler(handler)
